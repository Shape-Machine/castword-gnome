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
            text_block = next(
                (b for b in message.content if hasattr(b, "text")), None
            )
            if not text_block or not text_block.text.strip():
                raise ProviderError("Anthropic returned an empty response.")
            return text_block.text.strip()
        except anthropic.AuthenticationError as e:
            print(f"Anthropic auth error: {e}", flush=True)
            raise ProviderError("Invalid Anthropic API key — check Preferences → Providers.") from e
        except anthropic.RateLimitError as e:
            print(f"Anthropic rate limit: {e}", flush=True)
            raise ProviderError("Anthropic rate limit reached — try again in a moment.") from e
        except anthropic.APIConnectionError as e:
            print(f"Anthropic connection error: {e}", flush=True)
            raise ProviderError("Could not reach Anthropic — check your internet connection.") from e
        except anthropic.APIError as e:
            print(f"Anthropic error: {e}", flush=True)
            raise ProviderError("Anthropic request failed — try again.") from e

    async def aclose(self) -> None:
        await self._client.aclose()
