"""
Tone definitions and GSettings serialization.
"""

import json

from castword.providers.base import Tone


def default_tones() -> list[Tone]:
    return [
        Tone(
            name="Direct",
            system_prompt=(
                "Rewrite the following text to be direct and confident. Remove hedging, "
                "filler words, and passive constructions. Say exactly what needs to be "
                "said — nothing more. Return only the rewritten text."
            ),
        ),
        Tone(
            name="Technical",
            system_prompt=(
                "Rewrite the following text for a technical audience. Use clear, precise "
                "language. Structure the content with headings and bullet points where "
                "appropriate. Avoid vague phrasing. Return only the rewritten text."
            ),
        ),
        Tone(
            name="Professional",
            system_prompt=(
                "Rewrite the following text in a professional tone — polished and "
                "competent, but human and approachable. Suitable for emails, LinkedIn "
                "messages, and client communication. Use plain, globally readable "
                "English. Return only the rewritten text."
            ),
        ),
        Tone(
            name="Social",
            system_prompt=(
                "Rewrite the following text for social media. Make it punchy, engaging, "
                "and easy to read. You may use relevant emojis sparingly. Keep it concise "
                "and shareable. Return only the rewritten text."
            ),
        ),
        Tone(
            name="TL;DR",
            system_prompt=(
                "Summarise the following text in 1-2 sentences. Capture the core point "
                "only — no preamble, no explanation. Return only the summary."
            ),
            enabled=False,
        ),
        Tone(
            name="Flirty",
            system_prompt=(
                "Rewrite the following text in a flirty, charming tone. Keep it tasteful "
                "and fun. Return only the rewritten text."
            ),
            enabled=False,
        ),
        Tone(
            name="Playful",
            system_prompt=(
                "Rewrite the following text in a light, playful, and friendly tone. "
                "Keep it clear. Return only the rewritten text."
            ),
            enabled=False,
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
        enabled = item.get("enabled", True)
        if name and prompt:
            tones.append(Tone(name=name, system_prompt=prompt, enabled=bool(enabled)))

    return tones or default_tones()
