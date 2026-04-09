import httpx

from castword.providers.base import BaseProvider, ProviderError, Tone


class OllamaProvider(BaseProvider):
    def __init__(self, base_url: str = "http://localhost:11434", model: str = "llama3"):
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._client = httpx.AsyncClient(timeout=60.0)

    async def rewrite(self, text: str, tone: Tone) -> str:
        url = f"{self._base_url}/v1/chat/completions"
        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": tone.system_prompt},
                {"role": "user", "content": text},
            ],
            "temperature": 0.7,
        }
        try:
            response = await self._client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"].strip()
        except httpx.ConnectError:
            raise ProviderError(
                f"Could not connect to Ollama at {self._base_url}. "
                "Is Ollama running? Try: ollama serve"
            )
        except httpx.TimeoutException:
            raise ProviderError(
                f"Ollama request timed out. The model '{self._model}' may still be loading."
            )
        except httpx.HTTPStatusError as e:
            print(f"Ollama HTTP error: {e.response.status_code} {e.response.text}", flush=True)
            raise ProviderError(f"Ollama returned HTTP {e.response.status_code} — check the model name and try again.") from e
        except (KeyError, ValueError) as e:
            print(f"Ollama response parse error: {e}", flush=True)
            raise ProviderError("Unexpected response from Ollama — try again.") from e

    async def aclose(self) -> None:
        await self._client.aclose()
