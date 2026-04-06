from abc import ABC, abstractmethod


class BaseSpeechProvider(ABC):
    @abstractmethod
    async def transcribe(self, audio_bytes: bytes) -> str:
        """Transcribe audio bytes to text.

        Returns the transcribed string.
        Raises ProviderError on failure (Phase 2 implementations).
        Raises NotImplementedError for stub providers.
        """
