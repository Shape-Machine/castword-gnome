import openai

from castword.providers.base import BaseProvider, ProviderError, Tone


class OpenAIProvider(BaseProvider):
    def __init__(self, api_key: str, model: str = "gpt-4o"):
        self._client = openai.AsyncOpenAI(api_key=api_key)
        self._model = model

    async def rewrite(self, text: str, tone: Tone) -> str:
        try:
            response = await self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": tone.system_prompt},
                    {"role": "user", "content": text},
                ],
                temperature=0.7,
            )
            result = (response.choices[0].message.content or "").strip()
            if not result:
                raise ProviderError("OpenAI returned an empty response.")
            return result
        except openai.AuthenticationError as e:
            print(f"OpenAI auth error: {e}", flush=True)
            raise ProviderError("Invalid OpenAI API key — check Preferences → Providers.") from e
        except openai.RateLimitError as e:
            print(f"OpenAI rate limit: {e}", flush=True)
            raise ProviderError("OpenAI rate limit reached — try again in a moment.") from e
        except openai.APIConnectionError as e:
            print(f"OpenAI connection error: {e}", flush=True)
            raise ProviderError("Could not reach OpenAI — check your internet connection.") from e
        except openai.OpenAIError as e:
            print(f"OpenAI error: {e}", flush=True)
            raise ProviderError("OpenAI request failed — try again.") from e

    async def aclose(self) -> None:
        await self._client.aclose()
