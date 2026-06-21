"""Input validation and wikitext quality checkers for the translation assistant."""

from __future__ import annotations

import re
from collections import Counter
from typing import Any

import mwparserfromhell

LANG_CODE_PATTERN = re.compile(r"^[a-z]{2,3}(-[a-z]{2,4})?$")
TITLE_MIN_LENGTH = 1
TITLE_MAX_LENGTH = 255

# --- Template categories ---

CITATION_TEMPLATE_NAMES = frozenset(
    {
        "cite web",
        "cite news",
        "cite journal",
        "cite book",
        "cite magazine",
        "cite encyclopedia",
        "cite report",
        "cite thesis",
        "cite conference",
        "cite arxiv",
        "cite doi",
        "cite isbn",
        "cite pmid",
        "citation",
        "citation needed",
        "harvnb",
        "sfn",
    }
)

LOCALIZATION_TEMPLATE_NAMES = frozenset(
    {
        "authority control",
        "defaultsort",
        "short description",
        "navbox",
        "sidebar",
        "succession box",
        "s-start",
        "s-end",
        "portal",
        "commons category",
        "wikidata",
    }
)

KOREAN_STYLE_PATTERNS: list[tuple[str, str]] = [
    ("입니다", "이다"),
    ("합니다", "한다 / 하다"),
    ("습니다", "다 (문맥에 맞게 어미 조정)"),
    ("했습니다", "하였다"),
    ("있습니다", "있다"),
    ("없습니다", "없다"),
    ("됩니다", "된다"),
    ("되었습니다", "되었다"),
    ("쓰입니다", "쓰인다"),
    ("말합니다", "말한다"),
]

REF_OPEN_PATTERN = re.compile(r"<ref\b(?![^>]*/>)[^>]*>", re.IGNORECASE)
REF_SELF_CLOSING_PATTERN = re.compile(r"<ref\b[^>]*/>", re.IGNORECASE)
REF_CLOSE_PATTERN = re.compile(r"</ref>", re.IGNORECASE)
REF_NAME_PATTERN = re.compile(
    r'<ref\b[^>]*\bname\s*=\s*["\']([^"\']+)["\']',
    re.IGNORECASE,
)
REF_BLOCK_PATTERN = re.compile(
    r"<ref\b(?![^>]*/>)([^>]*)>(.*?)</ref>",
    re.IGNORECASE | re.DOTALL,
)

METADATA_PATTERNS: dict[str, re.Pattern[str]] = {
    "url": re.compile(r"\b(?:url|website)\s*=\s*([^\|\}\n]+)", re.IGNORECASE),
    "doi": re.compile(r"\bdoi\s*=\s*([^\|\}\n]+)", re.IGNORECASE),
    "isbn": re.compile(r"\bisbn\s*=\s*([^\|\}\n]+)", re.IGNORECASE),
    "pages": re.compile(
        r"\b(?:pages?|page)\s*=\s*([^\|\}\n]+)", re.IGNORECASE
    ),
    "access-date": re.compile(
        r"\b(?:access[- ]?date|accessdate)\s*=\s*([^\|\}\n]+)",
        re.IGNORECASE,
    ),
    "publisher": re.compile(r"\bpublisher\s*=\s*([^\|\}\n]+)", re.IGNORECASE),
    "title": re.compile(r"\btitle\s*=\s*([^\|\}\n]+)", re.IGNORECASE),
}


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


def _normalize_template_name(name: str) -> str:
    """Normalize a template name for comparison."""
    cleaned = str(name).strip().lower().replace("_", " ")
    # Strip namespace prefixes like "Template:"
    if cleaned.startswith("template:"):
        cleaned = cleaned.split(":", 1)[1].strip()
    return cleaned


def _extract_template_names(wikitext: str) -> list[str]:
    """Return normalized template names found in wikitext."""
    if not wikitext.strip():
        return []
    code = mwparserfromhell.parse(wikitext)
    return [_normalize_template_name(str(t.name)) for t in code.filter_templates()]


def _is_infobox(template_name: str) -> bool:
    normalized = _normalize_template_name(template_name)
    return normalized.startswith("infobox") or normalized in {"taxobox", "speciesbox", "chembox"}


def _is_citation_template(template_name: str) -> bool:
    normalized = _normalize_template_name(template_name)
    if normalized in CITATION_TEMPLATE_NAMES:
        return True
    return normalized.startswith("cite ")


def _count_citation_templates(template_names: list[str]) -> int:
    return sum(1 for name in template_names if _is_citation_template(name))


def _has_infobox(template_names: list[str]) -> bool:
    return any(_is_infobox(name) for name in template_names)


def _build_template_warnings_and_suggestions(
    source_names: list[str],
    translated_names: list[str],
    missing: list[str],
    extra: list[str],
) -> tuple[list[str], list[str]]:
    warnings: list[str] = []
    suggestions: list[str] = []

    source_set = set(source_names)
    translated_set = set(translated_names)

    if _has_infobox(source_names) and not _has_infobox(translated_names):
        warnings.append(
            "Source article contains an Infobox, but the translation draft does not. "
            "Infoboxes should usually be kept and localized."
        )
    elif _has_infobox(source_names) and _has_infobox(translated_names):
        suggestions.append(
            "Infobox detected in both source and translation. "
            "Review field labels and values for target-language localization."
        )

    source_cite_count = _count_citation_templates(source_names)
    translated_cite_count = _count_citation_templates(translated_names)
    if source_cite_count > translated_cite_count:
        warnings.append(
            f"Citation template count dropped from {source_cite_count} (source) "
            f"to {translated_cite_count} (translation). "
            "Do not remove citation templates during translation."
        )
    elif source_cite_count < translated_cite_count:
        warnings.append(
            f"Translation has more citation templates ({translated_cite_count}) "
            f"than source ({source_cite_count}). Verify each citation is backed "
            "by a reliable source — do not invent references."
        )

    for name in sorted(source_set & translated_set):
        if name in LOCALIZATION_TEMPLATE_NAMES:
            suggestions.append(
                f'Template "{name}" may need target-language localization '
                "(parameter names, sort keys, or category links)."
            )

    for name in missing:
        if _is_citation_template(name):
            warnings.append(
                f'Citation template "{name}" appears in source but is missing '
                "from the translation draft."
            )
        elif _is_infobox(name):
            warnings.append(
                f'Infobox-related template "{name}" is missing from the translation.'
            )
        elif name in LOCALIZATION_TEMPLATE_NAMES:
            suggestions.append(
                f'Localization template "{name}" is missing. '
                "Confirm whether it should be adapted for the target wiki."
            )
        else:
            warnings.append(
                f'Template "{name}" is present in source but missing in translation.'
            )

    for name in extra:
        if name not in LOCALIZATION_TEMPLATE_NAMES:
            warnings.append(
                f'Template "{name}" appears in translation but not in source. '
                "Verify it was added intentionally."
            )

    return warnings, suggestions


def check_templates(source_wikitext: str, translated_wikitext: str) -> dict[str, Any]:
    """
    Compare templates between source and translated wikitext.

    Returns counts, diffs, and human-readable warnings/suggestions.
    Does not modify wikitext.
    """
    source_names = _extract_template_names(source_wikitext)
    translated_names = _extract_template_names(translated_wikitext)

    source_unique = sorted(set(source_names))
    translated_unique = sorted(set(translated_names))
    missing = sorted(set(source_names) - set(translated_names))
    extra = sorted(set(translated_names) - set(source_names))

    warnings, suggestions = _build_template_warnings_and_suggestions(
        source_names, translated_names, missing, extra
    )

    return {
        "source_templates": source_names,
        "translated_templates": translated_names,
        "source_templates_unique": source_unique,
        "translated_templates_unique": translated_unique,
        "missing_templates": missing,
        "extra_templates": extra,
        "infobox_present_in_source": _has_infobox(source_names),
        "infobox_present_in_translation": _has_infobox(translated_names),
        "citation_templates_count_source": _count_citation_templates(source_names),
        "citation_templates_count_translation": _count_citation_templates(
            translated_names
        ),
        "warnings": warnings,
        "suggestions": suggestions,
    }


def _extract_named_refs(wikitext: str) -> set[str]:
    return {match.group(1).strip() for match in REF_NAME_PATTERN.finditer(wikitext)}


def _extract_ref_blocks(wikitext: str) -> list[str]:
    return [block.group(2) for block in REF_BLOCK_PATTERN.finditer(wikitext)]


def _extract_metadata_values(text: str) -> dict[str, list[str]]:
    values: dict[str, list[str]] = {key: [] for key in METADATA_PATTERNS}
    for key, pattern in METADATA_PATTERNS.items():
        for match in pattern.finditer(text):
            value = match.group(1).strip()
            if value:
                values[key].append(value)
    return values


def _collect_reference_metadata(wikitext: str) -> dict[str, list[str]]:
    """Collect bibliographic metadata from ref tags and citation templates."""
    combined = "\n".join(_extract_ref_blocks(wikitext))
    if not combined.strip():
        combined = wikitext

    code = mwparserfromhell.parse(wikitext)
    template_chunks = [str(t) for t in code.filter_templates() if _is_citation_template(str(t.name))]
    if template_chunks:
        combined += "\n" + "\n".join(template_chunks)

    return _extract_metadata_values(combined)


def _count_open_refs(wikitext: str) -> int:
    return len(REF_OPEN_PATTERN.findall(wikitext))


def _count_self_closing_refs(wikitext: str) -> int:
    return len(REF_SELF_CLOSING_PATTERN.findall(wikitext))


def _count_named_refs(wikitext: str) -> int:
    return len(_extract_named_refs(wikitext))


def _count_all_ref_tags(wikitext: str) -> int:
    return _count_open_refs(wikitext) + _count_self_closing_refs(wikitext)


def check_references(source_wikitext: str, translated_wikitext: str) -> dict[str, Any]:
    """
    Compare reference tags and bibliographic metadata between source and translation.

    Returns statistics, issues, and a reference_alignment_report.
    """
    source_stats = {
        "ref_tag_count": _count_all_ref_tags(source_wikitext),
        "named_ref_count": _count_named_refs(source_wikitext),
        "self_closing_ref_count": _count_self_closing_refs(source_wikitext),
        "citation_template_count": _count_citation_templates(
            _extract_template_names(source_wikitext)
        ),
        "ref_open_count": _count_open_refs(source_wikitext),
        "ref_close_count": len(REF_CLOSE_PATTERN.findall(source_wikitext)),
    }
    translated_stats = {
        "ref_tag_count": _count_all_ref_tags(translated_wikitext),
        "named_ref_count": _count_named_refs(translated_wikitext),
        "self_closing_ref_count": _count_self_closing_refs(translated_wikitext),
        "citation_template_count": _count_citation_templates(
            _extract_template_names(translated_wikitext)
        ),
        "ref_open_count": _count_open_refs(translated_wikitext),
        "ref_close_count": len(REF_CLOSE_PATTERN.findall(translated_wikitext)),
    }

    source_named = _extract_named_refs(source_wikitext)
    translated_named = _extract_named_refs(translated_wikitext)
    missing_ref_names = sorted(source_named - translated_named)
    extra_ref_names = sorted(translated_named - source_named)

    source_metadata = _collect_reference_metadata(source_wikitext)
    translated_metadata = _collect_reference_metadata(translated_wikitext)

    issues: list[dict[str, str]] = []
    warnings: list[str] = []

    for label, side in (("source", source_wikitext), ("translated", translated_wikitext)):
        opens = _count_open_refs(side)
        closes = len(REF_CLOSE_PATTERN.findall(side))
        if opens > closes:
            issues.append(
                {
                    "severity": "error",
                    "issue": f"Unclosed <ref> tags in {label} wikitext",
                    "detail": f"Opening tags: {opens}, closing tags: {closes}.",
                }
            )

    for name in missing_ref_names:
        issues.append(
            {
                "severity": "warning",
                "issue": f'Named ref "{name}" missing in translation',
                "detail": "Named references should be preserved for reuse across the article.",
            }
        )

    for name in extra_ref_names:
        issues.append(
            {
                "severity": "info",
                "issue": f'Named ref "{name}" only in translation',
                "detail": "Confirm this reference was added intentionally with a reliable source.",
            }
        )

    if source_stats["ref_tag_count"] > 0 and translated_stats["ref_tag_count"] == 0:
        issues.append(
            {
                "severity": "error",
                "issue": "Source has references but translation has none",
                "detail": "All factual content copied from the source should keep its references.",
            }
        )
    elif source_stats["ref_tag_count"] > translated_stats["ref_tag_count"]:
        issues.append(
            {
                "severity": "warning",
                "issue": "Reference count decreased in translation",
                "detail": (
                    f"Source refs: {source_stats['ref_tag_count']}, "
                    f"translation refs: {translated_stats['ref_tag_count']}."
                ),
            }
        )

    for field in METADATA_PATTERNS:
        source_values = source_metadata[field]
        translated_values = translated_metadata[field]
        if source_values and not translated_values:
            issues.append(
                {
                    "severity": "warning",
                    "issue": f'Metadata field "{field}" missing in translation',
                    "detail": (
                        f"Source has {len(source_values)} occurrence(s); "
                        "translation has none. Preserve URLs, DOIs, ISBNs, and page numbers."
                    ),
                }
            )
        elif source_values and len(translated_values) < len(source_values):
            issues.append(
                {
                    "severity": "warning",
                    "issue": f'Metadata field "{field}" count decreased',
                    "detail": (
                        f"Source: {len(source_values)}, translation: {len(translated_values)}."
                    ),
                }
            )

    source_plain_len = len(re.sub(r"<[^>]+>|\{\{.*?\}\}", "", source_wikitext, flags=re.DOTALL))
    translated_plain_len = len(
        re.sub(r"<[^>]+>|\{\{.*?\}\}", "", translated_wikitext, flags=re.DOTALL)
    )
    if (
        translated_plain_len > source_plain_len * 1.15
        and translated_stats["ref_tag_count"] <= source_stats["ref_tag_count"]
    ):
        issues.append(
            {
                "severity": "warning",
                "issue": "Translation may contain new unsourced content",
                "detail": (
                    "Translated text is longer but reference count did not increase. "
                    "Do not add AI-generated statements without reliable references."
                ),
            }
        )

    metadata_alignment = {
        field: {
            "source_count": len(source_metadata[field]),
            "translated_count": len(translated_metadata[field]),
            "preserved": bool(source_metadata[field]) == bool(translated_metadata[field])
            if not source_metadata[field]
            else len(translated_metadata[field]) >= len(source_metadata[field]),
        }
        for field in METADATA_PATTERNS
    }

    reference_alignment_report = {
        "source_stats": source_stats,
        "translated_stats": translated_stats,
        "missing_ref_names": missing_ref_names,
        "extra_ref_names": extra_ref_names,
        "metadata_alignment": metadata_alignment,
        "issues": issues,
        "warnings": warnings,
        "summary": (
            "References aligned"
            if not issues
            else f"{len(issues)} potential reference issue(s) found"
        ),
    }

    return reference_alignment_report


def check_korean_encyclopedic_style(text: str) -> list[dict[str, Any]]:
    """
    Detect formal/polite Korean endings (-입니다/-합니다 style) unsuitable for
    Korean Wikipedia's encyclopedic (-이다/-한다) style.

    Returns suggestions only — does not auto-replace text.
    """
    findings: list[dict[str, Any]] = []
    if not text.strip():
        return findings

    lines = text.splitlines()
    for line_number, line in enumerate(lines, start=1):
        for phrase, suggestion in KOREAN_STYLE_PATTERNS:
            start = 0
            while True:
                index = line.find(phrase, start)
                if index == -1:
                    break
                findings.append(
                    {
                        "problematic_phrase": phrase,
                        "line_number": line_number,
                        "approximate_position": index + 1,
                        "context": line.strip()[:120],
                        "suggestion": suggestion,
                    }
                )
                start = index + len(phrase)

    return findings
