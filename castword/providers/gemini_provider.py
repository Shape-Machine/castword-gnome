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
            if "API_KEY_INVALID" in str(e) or "UNAUTHENTICATED" in str(e):
                raise ProviderError(f"Gemini authentication failed: {e}") from e
            raise ProviderError(f"Gemini client error: {e}") from e
        except genai_errors.ServerError as e:
            raise ProviderError(f"Gemini server error: {e}") from e
        except Exception as e:
            raise ProviderError(f"Gemini error: {e}") from e
