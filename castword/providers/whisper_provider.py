import io

from openai import AsyncOpenAI

from castword.providers.base import ProviderError
from castword.providers.stt_base import BaseSpeechProvider, is_hallucination


class WhisperProvider(BaseSpeechProvider):
    """OpenAI Whisper cloud transcription."""

    def __init__(self, api_key: str, model: str = "whisper-1"):
        self._client = AsyncOpenAI(api_key=api_key)
        self._model = model

    async def transcribe(self, audio_bytes: bytes) -> str:
        if not audio_bytes:
            return ""
        try:
            response = await self._client.audio.transcriptions.create(
                file=("audio.wav", io.BytesIO(audio_bytes), "audio/wav"),
                model=self._model,
            )
            text = response.text
            return "" if is_hallucination(text) else text
        except Exception as exc:
            raise ProviderError(f"Whisper transcription failed: {exc}") from exc
