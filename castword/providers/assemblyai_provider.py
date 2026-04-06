import asyncio
import io

from castword.providers.base import ProviderError
from castword.providers.stt_base import BaseSpeechProvider


class AssemblyAIProvider(BaseSpeechProvider):
    """AssemblyAI cloud transcription."""

    def __init__(self, api_key: str):
        self._api_key = api_key

    async def transcribe(self, audio_bytes: bytes) -> str:
        try:
            import assemblyai as aai
        except ImportError:
            raise ProviderError(
                "assemblyai package not installed. Run: pip install assemblyai"
            )

        try:
            aai.settings.api_key = self._api_key
            transcriber = aai.Transcriber()
            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(
                None,
                transcriber.transcribe,
                io.BytesIO(audio_bytes),
            )
            if result.status == aai.TranscriptStatus.error:
                raise ProviderError(f"AssemblyAI error: {result.error}")
            return result.text or ""
        except ProviderError:
            raise
        except Exception as exc:
            raise ProviderError(f"AssemblyAI transcription failed: {exc}") from exc
