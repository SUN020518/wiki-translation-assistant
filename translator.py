"""Translation helpers for Wikipedia wikitext."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Any

try:
    import streamlit as st
except Exception:  # pragma: no cover - streamlit is available in the app runtime.
    st = None  # type: ignore[assignment]

PLACEHOLDER_MARKER = "[TRANSLATION PLACEHOLDER]"
DEFAULT_PROVIDER = "placeholder"
SUPPORTED_PROVIDERS = ("placeholder", "openai")
DEFAULT_OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
MAX_CHARS_PER_CHUNK = 3500
TEMPLATE_DENSE_TOKEN_RATIO = 0.55


@dataclass
class ProtectedText:
    """Text with wikitext-sensitive fragments replaced by stable tokens."""

    text: str
    token_map: dict[str, str]


def _placeholder_translation(text: str, source_lang: str, target_lang: str) -> str:
    header = (
        f"<!-- Draft translation: {source_lang} -> {target_lang} -->\n"
        f"<!-- {PLACEHOLDER_MARKER}: Replace this draft with human-reviewed translation -->\n\n"
    )
    return header + text


def _normalize_provider(provider: str) -> str:
    normalized = provider.strip().lower()
    return normalized if normalized in SUPPORTED_PROVIDERS else DEFAULT_PROVIDER


def get_openai_api_key() -> str | None:
    """
    Read an OpenAI API key from Streamlit secrets or environment variables.

    The key is never written to disk or logged.
    """
    if st is not None:
        try:
            key = st.secrets.get("OPENAI_API_KEY")  # type: ignore[union-attr]
            if key:
                return str(key)
        except Exception:
            pass
    return os.getenv("OPENAI_API_KEY")


def is_openai_configured() -> bool:
    """Return whether OpenAI mode can run with the current configuration."""
    return bool(get_openai_api_key())


def _make_token(prefix: str, index: int) -> str:
    return f"**{prefix}_{index}**"


def _protect_pattern(
    text: str,
    token_map: dict[str, str],
    pattern: str,
    prefix: str,
    flags: int = 0,
) -> str:
    """Replace regex matches with unique protected tokens."""
    counter = 0

    def replace(match: re.Match[str]) -> str:
        nonlocal counter
        token = _make_token(prefix, len(token_map) + counter)
        counter += 1
        token_map[token] = match.group(0)
        return token

    return re.sub(pattern, replace, text, flags=flags)


def protect_wikitext_tokens(text: str) -> tuple[str, dict[str, str]]:
    """
    Protect fragile wikitext fragments before sending text to an LLM.

    This is intentionally conservative. It preserves citations, templates, links,
    URLs, identifiers, and headings as opaque tokens so the model does not rewrite
    or corrupt them.
    """
    token_map: dict[str, str] = {}
    protected = text

    protected = _protect_pattern(
        protected,
        token_map,
        r"<ref\b[^>/]*?>.*?</ref>",
        "REF",
        flags=re.IGNORECASE | re.DOTALL,
    )
    protected = _protect_pattern(
        protected,
        token_map,
        r"<ref\b[^>]*?/>",
        "REF",
        flags=re.IGNORECASE | re.DOTALL,
    )
    protected = _protect_pattern(
        protected,
        token_map,
        r"\{\{\s*(?:cite\s+\w+|citation|sfn|harvnb|infobox)[\s\S]*?\}\}",
        "TEMPLATE",
        flags=re.IGNORECASE,
    )
    protected = _protect_pattern(
        protected,
        token_map,
        r"https?://[^\s\]\|}<>]+",
        "URL",
        flags=re.IGNORECASE,
    )
    protected = _protect_pattern(
        protected,
        token_map,
        r"\bdoi\s*=\s*[^\|\}\n]+|\b10\.\d{4,9}/[-._;()/:A-Z0-9]+",
        "DOI",
        flags=re.IGNORECASE,
    )
    protected = _protect_pattern(
        protected,
        token_map,
        r"\bisbn\s*=\s*[^\|\}\n]+|\bISBN(?:-1[03])?:?\s*[\d\- Xx]+",
        "ISBN",
        flags=re.IGNORECASE,
    )
    protected = _protect_pattern(
        protected,
        token_map,
        r"\[\[(?:File|Image|Category):[^\]]+\]\]",
        "WIKILINK",
        flags=re.IGNORECASE,
    )
    protected = _protect_pattern(
        protected,
        token_map,
        r"\[\[[^\]]+\]\]",
        "WIKILINK",
    )
    protected = _protect_pattern(
        protected,
        token_map,
        r"^\s*=+\s*[^=\n]+?\s*=+\s*$",
        "HEADING",
        flags=re.MULTILINE,
    )

    return protected, token_map


def restore_wikitext_tokens(text: str, token_map: dict[str, str]) -> str:
    """Restore protected wikitext fragments after translation."""
    restored = text
    for token, original in sorted(token_map.items(), key=lambda item: len(item[0]), reverse=True):
        restored = restored.replace(token, original)
    return restored


def get_translation_prompt(text: str, source_lang: str, target_lang: str) -> str:
    """Build the translation prompt sent to the LLM."""
    korean_instruction = (
        "\n- For Korean output, use encyclopedic plain style (-이다/-한다), not polite style."
        if target_lang.strip().lower() == "ko"
        else ""
    )
    return f"""Translate Wikipedia article text from {source_lang} to {target_lang}.

Rules:
- Preserve encyclopedic tone.
- Do not add new facts.
- Do not remove citations.
- Do not invent or modify references.
- Do not modify protected tokens such as **REF_0**, **TEMPLATE_0**, **URL_0**, **WIKILINK_0**, or **HEADING_0**.
- Preserve wikitext structure and headings.
- Return only translated wikitext, no explanation.{korean_instruction}

Text:
{text}
"""


def call_openai_translate(text: str, source_lang: str, target_lang: str) -> tuple[str, str | None]:
    """Translate a protected chunk with OpenAI. Returns (text, error)."""
    api_key = get_openai_api_key()
    if not api_key:
        return (
            text,
            "API key not configured. Please use placeholder mode or set OPENAI_API_KEY in Streamlit secrets.",
        )

    try:
        from openai import OpenAI
    except ImportError:
        return text, "OpenAI SDK is not installed. Run `pip install -r requirements.txt`."

    try:
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model=DEFAULT_OPENAI_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a careful Wikipedia translation assistant. "
                        "Translate only the supplied text and preserve protected tokens exactly."
                    ),
                },
                {
                    "role": "user",
                    "content": get_translation_prompt(text, source_lang, target_lang),
                },
            ],
            temperature=0.2,
        )
        translated = response.choices[0].message.content or ""
        return translated.strip(), None
    except Exception as exc:
        return text, f"OpenAI translation failed: {exc}"


def _split_wikitext_chunks(wikitext: str, max_chars: int = MAX_CHARS_PER_CHUNK) -> list[str]:
    """Split wikitext by headings/paragraphs while keeping chunks reasonably small."""
    lines = wikitext.splitlines(keepends=True)
    chunks: list[str] = []
    current = ""

    def flush() -> None:
        nonlocal current
        if current:
            chunks.append(current)
            current = ""

    for line in lines:
        is_heading = bool(re.match(r"^\s*=+\s*[^=\n]+?\s*=+\s*$", line.strip()))
        starts_new_paragraph = not line.strip()
        would_be_too_long = len(current) + len(line) > max_chars

        if current and (is_heading or starts_new_paragraph or would_be_too_long):
            flush()
        current += line
        if len(current) >= max_chars:
            flush()

    flush()
    return chunks or [wikitext]


def _is_template_dense(text: str) -> bool:
    """Return whether a chunk is mostly protected/template wikitext."""
    stripped = text.strip()
    if not stripped:
        return False
    template_chars = sum(len(match.group(0)) for match in re.finditer(r"\{\{[\s\S]*?\}\}", stripped))
    link_chars = sum(
        len(match.group(0))
        for match in re.finditer(r"\[\[(?:File|Image|Category):[^\]]+\]\]", stripped, flags=re.IGNORECASE)
    )
    return (template_chars + link_chars) / max(len(stripped), 1) >= TEMPLATE_DENSE_TOKEN_RATIO


def translate_text(
    text: str,
    source_lang: str,
    target_lang: str,
    provider: str = DEFAULT_PROVIDER,
) -> str:
    """
    Produce a draft translation for text.

    Kept as a string-returning compatibility wrapper for Phase 1-4 code.
    """
    provider = _normalize_provider(provider)
    if provider == "placeholder":
        return _placeholder_translation(text, source_lang, target_lang)

    protected, token_map = protect_wikitext_tokens(text)
    translated, error = call_openai_translate(protected, source_lang, target_lang)
    restored = restore_wikitext_tokens(translated, token_map)
    if error:
        return f"<!-- WARNING: {error} -->\n{restored}"
    return restored


def translate_wikitext_sections(
    wikitext: str,
    source_lang: str,
    target_lang: str,
    provider: str = DEFAULT_PROVIDER,
) -> dict[str, Any]:
    """
    Translate wikitext chunk-by-chunk while protecting fragile tokens.

    Returns metadata for the UI: translated wikitext, chunk count, provider, and warnings.
    """
    provider = _normalize_provider(provider)
    if provider == "placeholder":
        return {
            "translated_wikitext": _placeholder_translation(wikitext, source_lang, target_lang),
            "provider": provider,
            "chunk_count": 1,
            "warnings": [
                "Placeholder mode used. No AI translation was generated.",
                "Human proofreading is required before publication.",
            ],
        }

    warnings: list[str] = []
    chunks = _split_wikitext_chunks(wikitext)
    translated_chunks: list[str] = []

    for index, chunk in enumerate(chunks, start=1):
        if not chunk.strip():
            translated_chunks.append(chunk)
            continue

        if _is_template_dense(chunk):
            translated_chunks.append(chunk)
            warnings.append(f"Chunk {index} was template/media dense and kept unchanged.")
            continue

        protected, token_map = protect_wikitext_tokens(chunk)
        translated, error = call_openai_translate(protected, source_lang, target_lang)
        if error:
            translated_chunks.append(f"<!-- WARNING: {error} -->\n{chunk}")
            warnings.append(f"Chunk {index}: {error}")
            continue

        translated_chunks.append(restore_wikitext_tokens(translated, token_map))

    translated_wikitext = "".join(translated_chunks)
    warnings.append("AI-assisted draft generated. Human proofreading is required before publication.")
    warnings.append("Run template, reference, link, image, category, and final review checks before export.")

    return {
        "translated_wikitext": translated_wikitext,
        "provider": provider,
        "chunk_count": len(chunks),
        "warnings": warnings,
    }
