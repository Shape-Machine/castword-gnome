import asyncio
import os
import tempfile

from castword.providers.base import ProviderError
from castword.providers.stt_base import BaseSpeechProvider, is_hallucination


class WhisperLocalProvider(BaseSpeechProvider):
    """Local whisper.cpp transcription — shells out to the whisper.cpp binary."""

    def __init__(self, model_path: str, binary_path: str = "whisper"):
        self._model_path = model_path
        self._binary_path = binary_path or "whisper"

    async def transcribe(self, audio_bytes: bytes) -> str:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(audio_bytes)
            tmp_path = f.name

        txt_path = tmp_path + ".txt"
        try:
            proc = await asyncio.create_subprocess_exec(
                self._binary_path,
                "--model", self._model_path,
                "--output-txt",   # writes transcript to <input>.txt
                "--no-prints",    # suppress progress/log output
                "-nt",            # no timestamps in transcript
                tmp_path,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.PIPE,
            )
            _, stderr = await proc.communicate()
            if proc.returncode != 0:
                raise ProviderError(
                    f"whisper.cpp failed (exit {proc.returncode}): "
                    f"{stderr.decode().strip()}"
                )
            with open(txt_path) as f:
                text = f.read().strip()
            return "" if is_hallucination(text) else text
        except ProviderError:
            raise
        except FileNotFoundError:
            raise ProviderError(
                f"whisper.cpp binary not found at {self._binary_path!r}. "
                "Set the path in Preferences → Speech."
            )
        except Exception as exc:
            raise ProviderError(f"Local Whisper failed: {exc}") from exc
        finally:
            os.unlink(tmp_path)
            if os.path.exists(txt_path):
                os.unlink(txt_path)
