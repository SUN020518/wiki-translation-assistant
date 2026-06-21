"""Input validation for the translation assistant."""

from __future__ import annotations

import re

LANG_CODE_PATTERN = re.compile(r"^[a-z]{2,3}(-[a-z]{2,4})?$")
TITLE_MIN_LENGTH = 1
TITLE_MAX_LENGTH = 255


def validate_lang_code(code: str, field_name: str) -> tuple[bool, str]:
    """Validate a Wikipedia language code."""
    normalized = code.strip().lower()
    if not normalized:
        return False, f"{field_name} is required."
    if not LANG_CODE_PATTERN.match(normalized):
        return False, (
            f"{field_name} must be a valid language code "
            f'(e.g. "en", "ko", "zh"). Got: "{code}".'
        )
    return True, normalized


def validate_title(title: str) -> tuple[bool, str]:
    """Validate an article title."""
    stripped = title.strip()
    if len(stripped) < TITLE_MIN_LENGTH:
        return False, "Article title is required."
    if len(stripped) > TITLE_MAX_LENGTH:
        return False, f"Article title must be at most {TITLE_MAX_LENGTH} characters."
    return True, stripped
