"""
Scans common shell config files for LLM API keys.
Returns only what is found — never writes to disk.
"""

import os
import re
from pathlib import Path

# Candidate files to scan, in priority order
_CONFIG_FILES = [
    "~/.env",
    "~/.bashrc",
    "~/.bash_profile",
    "~/.profile",
    "~/.zshrc",
    "~/.zprofile",
    "~/.config/fish/config.fish",
    "~/.config/castword/.env",
]

# Map of env var name → provider key name
_KEY_MAP = {
    "OPENAI_API_KEY": "openai",
    "ANTHROPIC_API_KEY": "anthropic",
    "GEMINI_API_KEY": "gemini",
    "GOOGLE_API_KEY": "gemini",  # fallback name
}

# Matches: export KEY=value, KEY=value, set -x KEY value (fish)
_PATTERN = re.compile(
    r"""
    (?:export\s+|set\s+-[xgUl]*\s+)?   # optional export / fish set
    (?P<key>[A-Z_]+)                    # variable name
    [\s=]\s*                            # separator
    ['"]?(?P<value>[^'"\s#]+)['"]?      # value (optional quotes)
    """,
    re.VERBOSE,
)


def scan() -> dict[str, str]:
    """
    Scan shell config files for known API keys.

    Returns a dict mapping provider name to discovered key value,
    e.g. {"openai": "sk-...", "anthropic": "sk-ant-..."}.
    The live environment is checked first, then files in order —
    the first value found for each provider wins.
    """
    found: dict[str, str] = {}

    # Also check live environment first — most reliable source
    for env_var, provider in _KEY_MAP.items():
        value = os.environ.get(env_var)
        if value and provider not in found:
            found[provider] = value

    for path_str in _CONFIG_FILES:
        path = Path(path_str).expanduser()
        if not path.is_file():
            continue
        try:
            text = path.read_text(errors="ignore")
        except OSError:
            continue

        for match in _PATTERN.finditer(text):
            key = match.group("key")
            value = match.group("value").strip()
            if key in _KEY_MAP and value:
                provider = _KEY_MAP[key]
                if provider not in found:
                    found[provider] = value

    return found
