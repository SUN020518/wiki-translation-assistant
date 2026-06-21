"""Translation helpers for Wikipedia wikitext (MVP placeholder)."""

from __future__ import annotations

PLACEHOLDER_MARKER = "[TRANSLATION PLACEHOLDER]"


def translate_text(text: str, source_lang: str, target_lang: str) -> str:
    """
    Produce a draft translation for the given wikitext.

    MVP: returns the source text wrapped with a visible placeholder marker.
    A future version will call a real translation backend while preserving
    wikitext structure.

    Args:
        text: Source wikitext.
        source_lang: Source language code (e.g. "en").
        target_lang: Target language code (e.g. "ko").

    Returns:
        Draft wikitext with placeholder translation markers.
    """
    header = (
        f"<!-- Draft translation: {source_lang} -> {target_lang} -->\n"
        f"<!-- {PLACEHOLDER_MARKER}: Replace this draft with human-reviewed translation -->\n\n"
    )
    return header + text
