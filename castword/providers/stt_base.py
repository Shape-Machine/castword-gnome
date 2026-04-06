import re
from abc import ABC, abstractmethod

# Whisper hallucinates these phrases on silent or near-silent audio.
# Normalise to lowercase + strip punctuation for comparison.
_WHISPER_HALLUCINATIONS = {
    "thank you for watching",
    "thanks for watching",
    "thank you",
    "thanks",
    "please subscribe",
    "like and subscribe",
    "subscribe and like",
    "see you next time",
    "see you in the next video",
    "bye",
    "goodbye",
}

_STRIP_PUNCT = re.compile(r"[^\w\s]")


def is_hallucination(text: str) -> bool:
    """Return True if text is a known Whisper hallucination on silent audio."""
    normalised = _STRIP_PUNCT.sub("", text.lower()).strip()
    return normalised in _WHISPER_HALLUCINATIONS


class BaseSpeechProvider(ABC):
    @abstractmethod
    async def transcribe(self, audio_bytes: bytes) -> str:
        """Transcribe audio bytes to text.

        Returns the transcribed string (empty string if nothing was said).
        Raises ProviderError on failure.
        """
