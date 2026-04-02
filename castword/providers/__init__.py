from castword.providers.base import BaseProvider, ProviderError, Tone
from castword.providers.openai_provider import OpenAIProvider
from castword.providers.anthropic_provider import AnthropicProvider
from castword.providers.gemini_provider import GeminiProvider
from castword.providers.ollama_provider import OllamaProvider


def make_provider(settings) -> BaseProvider:
    """
    Instantiate the active provider from a Gio.Settings object.
    Raises ProviderError if the provider is misconfigured.
    """
    from gi.repository import Secret

    provider_name = settings.get_string("active-provider")

    if provider_name == "openai":
        key = _get_secret(Secret, "openai") or ""
        if not key:
            raise ProviderError("No OpenAI API key found. Add it in Preferences.")
        return OpenAIProvider(api_key=key, model=settings.get_string("openai-model"))

    if provider_name == "anthropic":
        key = _get_secret(Secret, "anthropic") or ""
        if not key:
            raise ProviderError("No Anthropic API key found. Add it in Preferences.")
        return AnthropicProvider(api_key=key, model=settings.get_string("anthropic-model"))

    if provider_name == "gemini":
        key = _get_secret(Secret, "gemini") or ""
        if not key:
            raise ProviderError("No Gemini API key found. Add it in Preferences.")
        return GeminiProvider(api_key=key, model=settings.get_string("gemini-model"))

    if provider_name == "ollama":
        return OllamaProvider(
            base_url=settings.get_string("ollama-base-url"),
            model=settings.get_string("ollama-model"),
        )

    raise ProviderError(f"Unknown provider: {provider_name!r}")


def _get_secret(Secret, provider: str) -> str | None:
    """Look up an API key from the GNOME Keyring."""
    return Secret.password_lookup_sync(
        _secret_schema(Secret),
        {"provider": provider},
        None,
    )


def store_secret(provider: str, api_key: str) -> None:
    """Store an API key in the GNOME Keyring."""
    from gi.repository import Secret
    Secret.password_store_sync(
        _secret_schema(Secret),
        {"provider": provider},
        Secret.COLLECTION_DEFAULT,
        f"castword {provider} API key",
        api_key,
        None,
    )


def lookup_secret(provider: str) -> str | None:
    """Retrieve an API key from the GNOME Keyring."""
    from gi.repository import Secret
    return _get_secret(Secret, provider)


def _secret_schema(Secret):
    return Secret.Schema.new(
        "xyz.shapemachine.castword-gnome",
        Secret.SchemaFlags.NONE,
        {"provider": Secret.SchemaAttributeType.STRING},
    )
