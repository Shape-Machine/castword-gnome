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
            raise ProviderError(f"OpenAI authentication failed: {e}") from e
        except openai.RateLimitError as e:
            raise ProviderError(f"OpenAI rate limit exceeded: {e}") from e
        except openai.APIConnectionError as e:
            raise ProviderError(f"Could not reach OpenAI: {e}") from e
        except openai.OpenAIError as e:
            raise ProviderError(f"OpenAI error: {e}") from e
