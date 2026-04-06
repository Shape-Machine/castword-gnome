import asyncio
import os
import tempfile

from castword.providers.base import ProviderError
from castword.providers.stt_base import BaseSpeechProvider


class WhisperLocalProvider(BaseSpeechProvider):
    """Local whisper.cpp transcription — shells out to the whisper.cpp binary."""

    def __init__(self, model_path: str, binary_path: str = "whisper"):
        self._model_path = model_path
        self._binary_path = binary_path or "whisper"

    async def transcribe(self, audio_bytes: bytes) -> str:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(audio_bytes)
            tmp_path = f.name

        try:
            proc = await asyncio.create_subprocess_exec(
                self._binary_path,
                "--model", self._model_path,
                "--output-txt",
                "--no-timestamps",
                tmp_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()
            if proc.returncode != 0:
                raise ProviderError(
                    f"whisper.cpp failed (exit {proc.returncode}): "
                    f"{stderr.decode().strip()}"
                )
            return stdout.decode().strip()
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
