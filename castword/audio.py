import io
import math
import struct
import threading
import time
import wave

import gi
from gi.repository import GLib

try:
    gi.require_version("Gst", "1.0")
    gi.require_version("GstApp", "1.0")
    from gi.repository import Gst
    Gst.init(None)
    _GST_AVAILABLE = True
except (ValueError, ImportError):
    _GST_AVAILABLE = False


class AudioRecorder:
    """Continuous microphone recorder with silence-based chunking.

    Runs a GStreamer pipeline (pulsesrc → level → appsink) and emits WAV
    chunks whenever a period of speech followed by silence is detected.
    Callbacks are always invoked on the GTK main thread via GLib.idle_add.
    """

    SILENCE_THRESHOLD_DB = -40.0   # RMS below this = silence (dBFS)
    SPEECH_THRESHOLD_DB  = -35.0   # RMS must exceed this to count as real speech for idle timer
    SILENCE_DURATION_S   = 1.5     # seconds of silence before emitting a chunk
    MAX_CHUNK_DURATION_S = 30.0    # safety flush regardless of silence
    IDLE_TIMEOUT_S       = 5.0     # auto-stop after this many seconds without speech
    MIN_CHUNK_RMS_DB     = -38.0   # discard chunks whose average energy is below this
    SAMPLE_RATE          = 16000

    _PIPELINE_STR = (
        "pulsesrc ! "
        "audioconvert ! "
        "audioresample ! "
        "audio/x-raw,rate=16000,channels=1,format=S16LE ! "
        "level name=level interval=100000000 ! "
        "appsink name=sink emit-signals=true max-buffers=200 drop=false"
    )

    def __init__(self, on_chunk, on_error, on_idle=None):
        """
        on_chunk(wav_bytes: bytes) — called on GTK main thread with a WAV buffer
        on_error(message: str)    — called on GTK main thread on pipeline error
        on_idle()                 — called on GTK main thread after IDLE_TIMEOUT_S
                                    of continuous silence with no speech
        """
        self._on_chunk = on_chunk
        self._on_error = on_error
        self._on_idle = on_idle
        self._pipeline = None
        self._bus_watch_id = None

        # PCM accumulation — protected by _lock (written from GStreamer thread)
        self._lock = threading.Lock()
        self._pcm_buffer = bytearray()

        # Silence / chunk state — only accessed on main thread (bus watch callback)
        self._has_speech = False
        self._silence_start: float | None = None
        self._chunk_start: float | None = None
        self._last_speech_time: float | None = None

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def start(self) -> None:
        if not _GST_AVAILABLE:
            GLib.idle_add(
                self._on_error,
                "GStreamer Python bindings not found.\n"
                "  Arch: sudo pacman -S python-gst gst-plugins-good\n"
                "  Debian/Ubuntu: sudo apt install python3-gst-1.0 gstreamer1.0-plugins-good",
            )
            return

        if self._pipeline is not None:
            return  # already running

        try:
            pipeline = Gst.parse_launch(self._PIPELINE_STR)
        except Exception as exc:
            GLib.idle_add(self._on_error, f"Failed to start microphone: {exc}")
            return
        if pipeline is None:
            GLib.idle_add(self._on_error, "Failed to start microphone pipeline.")
            return

        sink = pipeline.get_by_name("sink")
        sink.connect("new-sample", self._on_new_sample)

        bus = pipeline.get_bus()
        self._bus_watch_id = bus.add_watch(GLib.PRIORITY_DEFAULT, self._on_bus_message)

        with self._lock:
            self._pcm_buffer.clear()
        self._has_speech = False
        self._silence_start = None
        self._chunk_start = time.monotonic()
        self._last_speech_time = time.monotonic()  # enables idle timeout before first speech

        pipeline.set_state(Gst.State.PLAYING)
        self._pipeline = pipeline

    def stop(self) -> None:
        if self._pipeline is None:
            return

        # Flush any remaining speech before tearing down
        self._flush_chunk()

        self._pipeline.set_state(Gst.State.NULL)
        self._pipeline = None
        if self._bus_watch_id is not None:
            GLib.source_remove(self._bus_watch_id)
            self._bus_watch_id = None

        # Release buffer memory regardless of speech state
        with self._lock:
            self._pcm_buffer.clear()

    def is_running(self) -> bool:
        return self._pipeline is not None

    # ------------------------------------------------------------------ #
    # GStreamer callbacks
    # ------------------------------------------------------------------ #

    def _on_new_sample(self, sink):
        """Called on a GStreamer streaming thread — only touch _pcm_buffer."""
        sample = sink.emit("pull-sample")
        if sample is None:
            return Gst.FlowReturn.ERROR

        buf = sample.get_buffer()
        ok, mapinfo = buf.map(Gst.MapFlags.READ)
        if not ok:
            return Gst.FlowReturn.ERROR
        try:
            with self._lock:
                self._pcm_buffer.extend(mapinfo.data)
        finally:
            buf.unmap(mapinfo)

        return Gst.FlowReturn.OK

    def _on_bus_message(self, bus, message) -> bool:
        """Called on the GTK main thread via GLib bus watch."""
        if message.type == Gst.MessageType.ERROR:
            err, _debug = message.parse_error()
            if self._pipeline:
                self._pipeline.set_state(Gst.State.NULL)
                self._pipeline = None
            GLib.idle_add(self._on_error, f"Microphone error: {err.message}")
            return False  # remove watch

        if message.type == Gst.MessageType.ELEMENT:
            structure = message.get_structure()
            if structure and structure.get_name() == "level":
                self._handle_level(structure)

        return True  # keep watch

    # ------------------------------------------------------------------ #
    # Silence detection (main thread only)
    # ------------------------------------------------------------------ #

    def _handle_level(self, structure) -> None:
        try:
            rms_arr = structure.get_value("rms")
            rms_db: float = rms_arr[0]
        except (TypeError, IndexError, AttributeError):
            return

        now = time.monotonic()
        is_silent = rms_db < self.SILENCE_THRESHOLD_DB

        if not is_silent:
            self._has_speech = True
            self._silence_start = None
            if rms_db >= self.SPEECH_THRESHOLD_DB:
                self._last_speech_time = now
        else:
            if self._silence_start is None:
                self._silence_start = now
            # No speech yet — discard accumulated buffer to prevent unbounded growth
            if not self._has_speech:
                with self._lock:
                    self._pcm_buffer.clear()

        # Silence-based flush: speech detected and then silence for long enough
        if (self._has_speech and is_silent and self._silence_start is not None
                and (now - self._silence_start) >= self.SILENCE_DURATION_S):
            self._flush_chunk()
            return

        # Safety flush: chunk grown too long regardless of silence
        if (self._has_speech and self._chunk_start is not None
                and (now - self._chunk_start) >= self.MAX_CHUNK_DURATION_S):
            self._flush_chunk()
            return

        # Idle auto-stop: no speech at all for too long
        if (self._on_idle is not None
                and self._last_speech_time is not None
                and is_silent
                and (now - self._last_speech_time) >= self.IDLE_TIMEOUT_S):
            self._last_speech_time = None  # prevent repeated firing
            GLib.idle_add(self._on_idle)

    def _flush_chunk(self) -> None:
        """Emit accumulated PCM as a WAV chunk if it contains real speech."""
        with self._lock:
            if not self._has_speech or len(self._pcm_buffer) == 0:
                return
            pcm = bytes(self._pcm_buffer)
            self._pcm_buffer.clear()

        self._has_speech = False
        self._silence_start = None
        self._chunk_start = time.monotonic()

        # Discard chunks whose average energy is too low — likely background
        # noise that briefly crossed the per-frame silence threshold.
        if self._chunk_rms_db(pcm) < self.MIN_CHUNK_RMS_DB:
            return

        GLib.idle_add(self._on_chunk, self._pcm_to_wav(pcm))

    # ------------------------------------------------------------------ #
    # WAV encoding (stdlib only)
    # ------------------------------------------------------------------ #

    @staticmethod
    def _chunk_rms_db(pcm: bytes) -> float:
        """Return the RMS level of a S16LE PCM buffer in dBFS."""
        n = len(pcm) // 2
        if n == 0:
            return -math.inf
        samples = struct.unpack_from(f"<{n}h", pcm)
        mean_sq = sum(s * s for s in samples) / n
        rms_linear = math.sqrt(mean_sq) / 32768.0
        if rms_linear < 1e-9:
            return -math.inf
        return 20.0 * math.log10(rms_linear)

    @staticmethod
    def _pcm_to_wav(pcm: bytes, sample_rate: int = SAMPLE_RATE) -> bytes:
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)   # S16LE = 2 bytes per sample
            wf.setframerate(sample_rate)
            wf.writeframes(pcm)
        return buf.getvalue()
