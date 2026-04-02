import anthropic

from castword.providers.base import BaseProvider, ProviderError, Tone


class AnthropicProvider(BaseProvider):
    def __init__(self, api_key: str, model: str = "claude-opus-4-6"):
        self._client = anthropic.AsyncAnthropic(api_key=api_key)
        self._model = model

    async def rewrite(self, text: str, tone: Tone) -> str:
        try:
            message = await self._client.messages.create(
                model=self._model,
                max_tokens=4096,
                system=tone.system_prompt,
                messages=[{"role": "user", "content": text}],
            )
            return message.content[0].text.strip()
        except anthropic.AuthenticationError as e:
            raise ProviderError(f"Anthropic authentication failed: {e}") from e
        except anthropic.RateLimitError as e:
            raise ProviderError(f"Anthropic rate limit exceeded: {e}") from e
        except anthropic.APIConnectionError as e:
            raise ProviderError(f"Could not reach Anthropic: {e}") from e
        except anthropic.APIError as e:
            raise ProviderError(f"Anthropic error: {e}") from e
