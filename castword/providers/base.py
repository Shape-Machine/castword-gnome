from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class Tone:
    name: str
    system_prompt: str
    enabled: bool = True


class ProviderError(Exception):
    pass


class BaseProvider(ABC):
    @abstractmethod
    async def rewrite(self, text: str, tone: Tone) -> str:
        """Rewrite text in the given tone. Returns rewritten text only."""
