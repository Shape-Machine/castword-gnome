from castword.providers.stt_base import BaseSpeechProvider


class WhisperProvider(BaseSpeechProvider):
    """OpenAI Whisper cloud transcription (Phase 2 stub).

    Will use the openai SDK (already a dependency) to call
    client.audio.transcriptions.create() in Phase 2.
    """

    def __init__(self, api_key: str, model: str = "whisper-1"):
        self._api_key = api_key
        self._model = model

    async def transcribe(self, audio_bytes: bytes) -> str:
        raise NotImplementedError("Whisper transcription not yet implemented (Phase 2)")
