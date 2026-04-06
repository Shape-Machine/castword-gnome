from castword.providers.stt_base import BaseSpeechProvider


class WhisperLocalProvider(BaseSpeechProvider):
    """Local whisper.cpp transcription (Phase 2 stub).

    Will shell out to the whisper.cpp binary with the configured model
    file in Phase 2.
    """

    def __init__(self, model_path: str):
        self._model_path = model_path

    async def transcribe(self, audio_bytes: bytes) -> str:
        raise NotImplementedError("Local Whisper transcription not yet implemented (Phase 2)")
