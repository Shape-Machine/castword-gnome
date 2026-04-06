import gi
try:
    gi.require_version("Secret", "1")
except ValueError:
    pass  # libsecret not available; make_provider will raise a friendly ProviderError

from castword.providers.base import BaseProvider, ProviderError, Tone
from castword.providers.openai_provider import OpenAIProvider
from castword.providers.anthropic_provider import AnthropicProvider
from castword.providers.gemini_provider import GeminiProvider
from castword.providers.ollama_provider import OllamaProvider
from castword.providers.stt_base import BaseSpeechProvider
from castword.providers.whisper_provider import WhisperProvider
from castword.providers.whisper_local_provider import WhisperLocalProvider
from castword.providers.assemblyai_provider import AssemblyAIProvider


def make_provider(settings, provider_id: str | None = None) -> BaseProvider:
    """
    Instantiate the active provider from a Gio.Settings object.
    Pass provider_id to override the active-provider setting.
    Raises ProviderError if the provider is misconfigured.
    """
    try:
        from gi.repository import Secret
    except (ImportError, ValueError):
        raise ProviderError(
            "libsecret is not installed. Install it with:\n"
            "  Arch: sudo pacman -S libsecret\n"
            "  Debian/Ubuntu: sudo apt install libsecret-1-0 gir1.2-secret-1"
        )

    provider_name = provider_id or settings.get_string("active-provider")

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


def make_stt_provider(settings) -> BaseSpeechProvider:
    """Instantiate the active STT provider from a Gio.Settings object.

    Returns a stub provider (all raise NotImplementedError in Phase 2).
    Raises ProviderError if the provider ID is unknown or misconfigured.
    """
    name = settings.get_string("active-stt-provider")

    if name == "whisper":
        key = lookup_secret("openai") or ""
        if not key:
            raise ProviderError("No OpenAI API key found. Add it in Preferences → Providers.")
        return WhisperProvider(api_key=key, model=settings.get_string("whisper-model"))

    if name == "whisper-local":
        return WhisperLocalProvider(
            model_path=settings.get_string("whisper-local-model-path")
        )

    if name == "assemblyai":
        key = lookup_secret("assemblyai") or ""
        if not key:
            raise ProviderError("No AssemblyAI API key found. Add it in Preferences → Speech.")
        return AssemblyAIProvider(api_key=key)

    raise ProviderError(f"Unknown STT provider: {name!r}")


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


_schema_cache = None


def _secret_schema(Secret):
    global _schema_cache
    if _schema_cache is None:
        _schema_cache = Secret.Schema.new(
            "xyz.shapemachine.castword-gnome",
            Secret.SchemaFlags.NONE,
            {"provider": Secret.SchemaAttributeType.STRING},
        )
    return _schema_cache
