"""
Tone definitions and GSettings serialization.
"""

import json

from castword.providers.base import Tone


def default_tones() -> list[Tone]:
    return [
        Tone(
            name="Formal",
            system_prompt=(
                "Rewrite the following text in a formal, professional tone. "
                "Preserve the meaning exactly. Return only the rewritten text."
            ),
        ),
        Tone(
            name="Concise",
            system_prompt=(
                "Rewrite the following text to be as concise as possible without "
                "losing meaning. Cut filler words. Return only the rewritten text."
            ),
        ),
        Tone(
            name="Playful",
            system_prompt=(
                "Rewrite the following text in a light, playful, and friendly tone. "
                "Keep it clear. Return only the rewritten text."
            ),
        ),
        Tone(
            name="Executive",
            system_prompt=(
                "Rewrite the following text in a direct, executive tone suited for "
                "senior leadership. Lead with the point. Return only the rewritten text."
            ),
        ),
        Tone(
            name="Friendly",
            system_prompt=(
                "Rewrite the following text in a warm, approachable, and conversational "
                "tone. Return only the rewritten text."
            ),
        ),
        Tone(
            name="Direct",
            system_prompt=(
                "Rewrite the following text to be blunt and direct. No hedging, no "
                "filler. Return only the rewritten text."
            ),
        ),
    ]


def tones_from_settings(settings) -> list[Tone]:
    """Parse the GSettings 'tones' JSON string into a list of Tone objects."""
    raw = settings.get_string("tones")
    try:
        items = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return default_tones()

    if not isinstance(items, list):
        return default_tones()

    tones = []
    for item in items:
        if not isinstance(item, dict):
            continue
        name = item.get("name", "").strip()
        prompt = item.get("system_prompt", "").strip()
        if name and prompt:
            tones.append(Tone(name=name, system_prompt=prompt))

    return tones or default_tones()
