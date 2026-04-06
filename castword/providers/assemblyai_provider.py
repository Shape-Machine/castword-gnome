from castword.providers.stt_base import BaseSpeechProvider


class AssemblyAIProvider(BaseSpeechProvider):
    """AssemblyAI cloud transcription (Phase 2 stub).

    Will use the assemblyai SDK to call the transcription API in Phase 2.
    """

    def __init__(self, api_key: str):
        self._api_key = api_key

    async def transcribe(self, audio_bytes: bytes) -> str:
        raise NotImplementedError("AssemblyAI transcription not yet implemented (Phase 2)")
