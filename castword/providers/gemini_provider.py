from google import genai
from google.genai import errors as genai_errors

from castword.providers.base import BaseProvider, ProviderError, Tone


class GeminiProvider(BaseProvider):
    def __init__(self, api_key: str, model: str = "gemini-2.0-flash"):
        self._client = genai.Client(api_key=api_key)
        self._model = model

    async def rewrite(self, text: str, tone: Tone) -> str:
        try:
            response = await self._client.aio.models.generate_content(
                model=self._model,
                contents=text,
                config=genai.types.GenerateContentConfig(
                    system_instruction=tone.system_prompt,
                    temperature=0.7,
                ),
            )
            if not response.text:
                reason = getattr(response.prompt_feedback, "block_reason", "unknown")
                raise ProviderError(f"Gemini blocked the response (reason: {reason}).")
            return response.text.strip()
        except genai_errors.ClientError as e:
            print(f"Gemini client error: {e}", flush=True)
            if "API_KEY_INVALID" in str(e) or "UNAUTHENTICATED" in str(e):
                raise ProviderError("Invalid Gemini API key — check Preferences → Providers.") from e
            raise ProviderError("Gemini request failed — try again.") from e
        except genai_errors.ServerError as e:
            print(f"Gemini server error: {e}", flush=True)
            raise ProviderError("Gemini server error — try again in a moment.") from e
        except Exception as e:
            print(f"Gemini error: {e}", flush=True)
            raise ProviderError("Gemini request failed — try again.") from e

    async def aclose(self) -> None:
        fn = getattr(self._client, "aclose", None) or getattr(self._client, "close", None)
        if callable(fn):
            result = fn()
            if hasattr(result, "__await__"):
                await result
