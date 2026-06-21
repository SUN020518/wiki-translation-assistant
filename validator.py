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

FILE_PREFIXES = ("file:", "image:")
CATEGORY_PREFIX = "category:"
SKIPPED_LINK_PREFIXES = (
    "file:",
    "image:",
    "category:",
    "template:",
    "help:",
    "wikipedia:",
    "wp:",
    "special:",
)

TEMPORARY_LINK_TEMPLATE_SUGGESTIONS = {
    "ko": "ko:틀:임시링크",
    "zh": "zh:Template:Internal link helper",
    "en": "Template:Interlanguage link",
}

REFERENCE_SECTION_TITLES = {
    "en": ("references",),
    "ko": ("각주",),
    "zh": ("参考资料", "參考資料"),
}

LANGUAGE_LABELS = {
    "en": {"en": "English", "ko": "영어", "zh": "英文"},
    "ko": {"en": "Korean", "ko": "한국어", "zh": "韩文"},
    "zh": {"en": "Chinese", "ko": "중국어", "zh": "中文"},
    "ja": {"en": "Japanese", "ko": "일본어", "zh": "日文"},
}

TALK_PAGE_TEMPLATE_CONFIG = {
    "ko": {
        "translated": "ko:틀:번역된_문서",
        "educational": "ko:틀:과제 문서",
        "translated_markup": "{{{{번역된 문서|{source_lang}|{source_title}|판={revision_id}}}}}",
        "educational_markup": "{{{{과제 문서}}}}",
    },
    "zh": {
        "translated": "zh:Template:Translated page",
        "educational": "zh:Template:Educational assignment",
        "translated_markup": "{{{{Translated page|{source_lang}|{source_title}|version={revision_id}}}}}",
        "educational_markup": "{{{{Educational assignment}}}}",
    },
    "en": {
        "translated": "Template:Translated page",
        "educational": "{{Educational assignment}}",
        "translated_markup": "{{{{Translated page|{source_lang}|{source_title}|version={revision_id}}}}}",
        "educational_markup": "{{{{Educational assignment}}}}",
    },
}

PROMOTIONAL_TERMS = (
    "best",
    "leading",
    "world-class",
    "revolutionary",
    "innovative solution",
    "최고",
    "혁신적",
    "领先",
    "最佳",
)

SUSPICIOUS_URL_PATTERNS = (
    "bit.ly",
    "tinyurl.com",
    "t.co/",
    "goo.gl",
    "adf.ly",
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


def _split_wikilink_target(raw_target: str) -> str:
    """Remove anchors from a wikilink target while keeping the page title."""
    return raw_target.split("#", 1)[0].strip()


def _normalize_page_title(title: str) -> str:
    """Normalize whitespace and underscores in a page/category/file title."""
    return " ".join(title.replace("_", " ").strip().split())


def _is_regular_internal_link(target: str) -> bool:
    normalized = target.strip().lower()
    if not normalized or normalized.startswith("#"):
        return False
    if ":" in normalized:
        return not normalized.startswith(SKIPPED_LINK_PREFIXES)
    return True


def extract_internal_links(wikitext: str) -> list[dict[str, str]]:
    """
    Extract regular article internal links from wikitext.

    File, image, category, template, help, and special namespace links are excluded.
    """
    if not wikitext.strip():
        return []

    code = mwparserfromhell.parse(wikitext)
    links: list[dict[str, str]] = []
    for wikilink in code.filter_wikilinks():
        raw_target = str(wikilink.title).strip()
        target = _normalize_page_title(_split_wikilink_target(raw_target))
        if not _is_regular_internal_link(target):
            continue

        display_text = str(wikilink.text).strip() if wikilink.text else ""
        links.append(
            {
                "source_link": str(wikilink),
                "target": target,
                "display_text": display_text,
            }
        )

    return links


def _temporary_link_template_for(target_lang: str) -> str:
    normalized = target_lang.strip().lower()
    return TEMPORARY_LINK_TEMPLATE_SUGGESTIONS.get(
        normalized,
        "Template:Interlanguage link or the target wiki's local temporary link template",
    )


def check_links(
    source_wikitext: str,
    source_lang: str,
    target_lang: str,
    target_page_candidates: dict[str, str] | None = None,
    target_page_statuses: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """
    Build a blue/red link risk report for source internal links.

    API lookups are provided by the caller so this function stays focused on
    wikitext analysis and report generation.
    """
    internal_links = extract_internal_links(source_wikitext)
    candidates = target_page_candidates or {}
    statuses = target_page_statuses or {}
    temporary_template = _temporary_link_template_for(target_lang)

    report_rows: list[dict[str, Any]] = []
    for link in internal_links:
        source_target = link["target"]
        target_candidate = candidates.get(source_target, source_target)
        status_info = statuses.get(target_candidate, {})
        exists = bool(status_info.get("exists"))
        possible_disambiguation = bool(status_info.get("possible_disambiguation"))

        if exists:
            status = "blue link"
            suggestion = "Can link to the target-language page after human review."
        elif target_candidate in statuses:
            status = "red link risk"
            suggestion = (
                f"Target page may not exist. Consider using temporary link template: "
                f"{temporary_template}."
            )
        else:
            status = "unknown"
            suggestion = "Could not verify this target page. Check manually before publishing."

        report_rows.append(
            {
                "source_link": link["source_link"],
                "source_target": source_target,
                "display_text": link["display_text"],
                "source_language": source_lang,
                "target_language": target_lang,
                "target_page_candidate": target_candidate,
                "status": status,
                "suggestion": suggestion,
                "possible_disambiguation": possible_disambiguation,
                "disambiguation_suggestion": (
                    "Please confirm this link points to the correct article, not a disambiguation page."
                    if possible_disambiguation
                    else ""
                ),
            }
        )

    status_counts = Counter(row["status"] for row in report_rows)
    disambiguation_warnings = [
        {
            "link": row["source_link"],
            "target_page_candidate": row["target_page_candidate"],
            "possible_disambiguation": True,
            "suggestion": row["disambiguation_suggestion"],
        }
        for row in report_rows
        if row["possible_disambiguation"]
    ]

    return {
        "source_internal_links": internal_links,
        "blue_link_alignment_report": report_rows,
        "summary": {
            "total_internal_links": len(report_rows),
            "blue_links": status_counts.get("blue link", 0),
            "red_link_risks": status_counts.get("red link risk", 0),
            "unknown": status_counts.get("unknown", 0),
            "possible_disambiguation_count": len(disambiguation_warnings),
        },
        "temporary_link_template_suggestion": temporary_template,
        "disambiguation_warnings": disambiguation_warnings,
    }


def extract_image_files(wikitext: str) -> list[dict[str, str]]:
    """Extract File:/Image: wikilinks from wikitext."""
    if not wikitext.strip():
        return []

    code = mwparserfromhell.parse(wikitext)
    images: list[dict[str, str]] = []
    for wikilink in code.filter_wikilinks():
        raw_target = str(wikilink.title).strip()
        normalized = raw_target.lower().replace("_", " ")
        if not normalized.startswith(FILE_PREFIXES):
            continue

        file_name = raw_target.split(":", 1)[1].strip() if ":" in raw_target else raw_target
        images.append(
            {
                "raw_link": str(wikilink),
                "file_name": _normalize_page_title(file_name),
                "namespace": raw_target.split(":", 1)[0],
            }
        )

    return images


def extract_categories(wikitext: str) -> list[str]:
    """Extract category names from wikitext."""
    if not wikitext.strip():
        return []

    code = mwparserfromhell.parse(wikitext)
    categories: list[str] = []
    for wikilink in code.filter_wikilinks():
        raw_target = str(wikilink.title).strip()
        if raw_target.lower().replace("_", " ").startswith(CATEGORY_PREFIX):
            category_name = raw_target.split(":", 1)[1].strip()
            categories.append(_normalize_page_title(category_name))

    return categories


def check_images_and_categories(
    source_wikitext: str,
    translated_wikitext: str,
) -> dict[str, Any]:
    """Check image links and category presence without downloading or uploading media."""
    source_categories = extract_categories(source_wikitext)
    translated_categories = extract_categories(translated_wikitext)
    image_files = extract_image_files(source_wikitext)

    missing_categories_warning = ""
    if source_categories and not translated_categories:
        missing_categories_warning = (
            "Source article has categories, but the translation draft has none. "
            "Add appropriate target-wiki categories before publishing."
        )
    elif not translated_categories:
        missing_categories_warning = (
            "No categories detected in the translation draft. New articles should usually "
            "include target-wiki categories."
        )

    copyright_warnings = [
        "Wikimedia Commons free-license images are usually safer, but still require review.",
        "Fair use images may not be allowed on Korean Wikipedia.",
        "Chinese Wikipedia has its own non-free content rules.",
        "Do not copy images from the internet unless licensing is clearly compatible.",
        "This tool does not download, upload, or license-check images automatically.",
    ]

    return {
        "image_files_detected": image_files,
        "source_categories": source_categories,
        "translated_categories": translated_categories,
        "missing_categories_warning": missing_categories_warning,
        "copyright_warnings": copyright_warnings,
    }


def check_references_section(text: str, target_lang: str) -> dict[str, Any]:
    """Check whether a target-language references section heading appears."""
    normalized_lang = target_lang.strip().lower()
    expected_titles = REFERENCE_SECTION_TITLES.get(
        normalized_lang,
        ("references", "参考资料", "參考資料", "각주"),
    )

    headings = [
        match.group(1).strip()
        for match in re.finditer(r"^\s*==+\s*(.*?)\s*==+\s*$", text, re.MULTILINE)
    ]
    normalized_headings = {heading.strip().lower() for heading in headings}
    found = any(title.lower() in normalized_headings for title in expected_titles)

    warning = ""
    if not found:
        warning = (
            "No expected references section heading was detected. Add the target-wiki "
            "references section before publishing if the article contains citations."
        )

    return {
        "target_language": normalized_lang,
        "expected_headings": list(expected_titles),
        "headings_detected": headings,
        "references_section_present": found,
        "missing_references_section_warning": warning,
    }


def check_wiki_structure(
    translated_wikitext: str,
    target_lang: str,
    disambiguation_warnings: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Combine structural reminders used before manual publication."""
    references_section = check_references_section(translated_wikitext, target_lang)
    return {
        "references_section": references_section,
        "disambiguation_warnings": disambiguation_warnings or [],
        "publishing_structure_reminders": [
            "Confirm the article has an appropriate lead, sections, references, and categories.",
            "Review all blue links and red links manually before publishing.",
            "Use temporary interlanguage link templates only when appropriate for the target wiki.",
            "Do not publish directly from this tool; use your Wikipedia sandbox and review checklist.",
        ],
    }


def _language_label(lang: str, output_lang: str) -> str:
    normalized = lang.strip().lower()
    return LANGUAGE_LABELS.get(normalized, {}).get(output_lang, normalized)


def _talk_page_config(target_lang: str) -> dict[str, str]:
    return TALK_PAGE_TEMPLATE_CONFIG.get(
        target_lang.strip().lower(),
        TALK_PAGE_TEMPLATE_CONFIG["en"],
    )


def generate_talk_page_templates(
    source_lang: str,
    source_title: str,
    target_lang: str,
    target_title: str,
    revision_id: str = "",
) -> dict[str, Any]:
    """Generate copy-ready talk page template suggestions."""
    config = _talk_page_config(target_lang)
    revision_value = revision_id.strip() or "REPLACE_WITH_SOURCE_REVISION_ID"
    translated_markup = config["translated_markup"].format(
        source_lang=source_lang,
        source_title=source_title,
        target_lang=target_lang,
        target_title=target_title,
        revision_id=revision_value,
    )
    educational_markup = config["educational_markup"].format(
        source_lang=source_lang,
        source_title=source_title,
        target_lang=target_lang,
        target_title=target_title,
        revision_id=revision_value,
    )

    copy_ready = "\n".join(
        [
            "<!-- Place these templates on the talk page, not in the article body. -->",
            translated_markup,
            educational_markup,
        ]
    )

    return {
        "talk_page_templates": [config["translated"], config["educational"]],
        "copy_ready_talk_page_wikitext": copy_ready,
        "explanation": (
            "Use these templates to disclose that the article was translated and, "
            "if applicable, created or edited as part of an educational assignment."
        ),
        "where_to_place": "Talk page",
        "source_language": source_lang,
        "source_title": source_title,
        "target_language": target_lang,
        "target_title": target_title,
    }


def generate_translation_attribution(
    source_lang: str,
    source_title: str,
    target_lang: str,
    target_title: str,
) -> dict[str, Any]:
    """Generate edit-summary attribution guidance for translated articles."""
    normalized_target = target_lang.strip().lower()
    source_label_en = _language_label(source_lang, "en")
    source_label_ko = _language_label(source_lang, "ko")
    source_label_zh = _language_label(source_lang, "zh")

    if normalized_target == "ko":
        edit_summary = (
            f'한국어 번역: {source_label_ko} 위키백과 "{source_title}" 문서에서 번역함.'
        )
    elif normalized_target == "zh":
        edit_summary = (
            f"翻译自{source_label_zh}维基百科条目“{source_title}”，"
            "版权归其贡献者所有，见原文历史记录。"
        )
    else:
        edit_summary = (
            f'Translated from {source_label_en} Wikipedia article "{source_title}"; '
            "see its history for attribution."
        )

    return {
        "recommended_edit_summary": edit_summary,
        "attribution_warning": (
            "Wikipedia translations must preserve attribution. Include a clear edit "
            "summary and consider adding the translated-page template on the talk page."
        ),
        "talk_page_translated_template": _talk_page_config(target_lang)["translated"],
        "reminder_to_check_original_history": (
            f'Before publishing "{target_title}", open the source article history for '
            f'"{source_title}" and confirm the translated revision.'
        ),
    }


def generate_educational_assignment_helper(target_lang: str) -> dict[str, str]:
    """Generate educational-assignment template guidance."""
    config = _talk_page_config(target_lang)
    return {
        "template_name": config["educational"],
        "where_to_place": "Talk page",
        "copy_ready_template": config["educational_markup"].format(
            source_lang="",
            source_title="",
            target_lang=target_lang,
            target_title="",
            revision_id="",
        ),
        "warning": (
            "Educational assignment templates belong on the talk page, not in the "
            "article page body."
        ),
    }


def build_page_move_checklist(
    translated_wikitext: str,
    target_lang: str,
    target_title: str,
    page_status: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a manual checklist for moving or publishing a draft to mainspace."""
    normalized_title = target_title.strip()
    lower_title = normalized_title.lower()
    namespace = "mainspace"
    if lower_title.startswith("user:") or lower_title.startswith("사용자:"):
        namespace = "user"
    elif lower_title.startswith("draft:") or lower_title.startswith("초안:"):
        namespace = "draft"

    references_section = check_references_section(translated_wikitext, target_lang)
    categories = extract_categories(translated_wikitext)
    status = page_status or {}
    title_exists = bool(status.get("exists"))

    checklist = [
        {
            "item": "Confirm draft namespace",
            "status": "needs_review" if namespace in {"user", "draft"} else "manual",
            "detail": (
                f"Current title appears to be in {namespace} namespace. "
                "If this is a new article, move the page to mainspace instead of copy-pasting."
            )
            if namespace in {"user", "draft"}
            else "Target title appears to be mainspace; confirm manually.",
        },
        {
            "item": "Preserve edit history",
            "status": "manual",
            "detail": "Move drafts to mainspace when appropriate to preserve edit history.",
        },
        {
            "item": "Check target title availability",
            "status": "needs_review" if title_exists else "manual",
            "detail": (
                "Target title may already exist; review existing page and history before publishing."
                if title_exists
                else "Target title was not found by the page-status check; confirm manually before publishing."
            ),
        },
        {
            "item": "Redirect handling",
            "status": "manual",
            "detail": "Decide whether redirects are needed after moving or renaming the draft.",
        },
        {
            "item": "Naming convention",
            "status": "manual",
            "detail": "Confirm the title follows target-language Wikipedia naming conventions.",
        },
        {
            "item": "References section",
            "status": "passed" if references_section["references_section_present"] else "missing",
            "detail": (
                "Expected references section found."
                if references_section["references_section_present"]
                else references_section["missing_references_section_warning"]
            ),
        },
        {
            "item": "Categories",
            "status": "passed" if categories else "missing",
            "detail": (
                f"{len(categories)} categor(ies) detected. Confirm they are blue-linked."
                if categories
                else "No categories detected. Add appropriate target-wiki categories."
            ),
        },
        {
            "item": "Interlanguage links",
            "status": "manual",
            "detail": "Confirm interlanguage links / Wikidata sitelinks after publication if applicable.",
        },
        {
            "item": "Post-publication monitoring",
            "status": "manual",
            "detail": "Monitor article history and talk page after publishing.",
        },
    ]

    return {
        "current_namespace_guess": namespace,
        "target_title_exists": title_exists,
        "references_section_present": references_section["references_section_present"],
        "categories_count": len(categories),
        "checklist": checklist,
        "reminder": (
            "This tool does not move pages. Use Wikipedia's normal page move workflow "
            "only after human review."
        ),
    }


def _count_external_links(text: str) -> int:
    return len(re.findall(r"https?://[^\s\]\|}<>]+", text, flags=re.IGNORECASE))


def check_edit_filter_risk(
    source_wikitext: str,
    translated_wikitext: str,
    target_lang: str,
    reference_report: dict[str, Any] | None = None,
    template_report: dict[str, Any] | None = None,
    attribution_prepared: bool = False,
    human_proofreading_confirmed: bool = False,
) -> dict[str, Any]:
    """
    Estimate edit-filter / moderation risk and suggest compliance fixes.

    This never suggests bypassing filters; it only recommends safer, policy-compliant edits.
    """
    reference_report = reference_report or check_references(source_wikitext, translated_wikitext)
    template_report = template_report or check_templates(source_wikitext, translated_wikitext)
    korean_style_findings = check_korean_encyclopedic_style(translated_wikitext)

    risk_reasons: list[str] = []
    suggested_fixes: list[str] = []

    source_plain_len = len(re.sub(r"<[^>]+>|\{\{.*?\}\}", "", source_wikitext, flags=re.DOTALL))
    translated_plain_len = len(
        re.sub(r"<[^>]+>|\{\{.*?\}\}", "", translated_wikitext, flags=re.DOTALL)
    )
    source_refs = reference_report["source_stats"]["ref_tag_count"]
    translated_refs = reference_report["translated_stats"]["ref_tag_count"]
    external_links = _count_external_links(translated_wikitext)
    citation_templates = reference_report["translated_stats"]["citation_template_count"]
    suspicious_urls = [
        pattern
        for pattern in SUSPICIOUS_URL_PATTERNS
        if pattern in translated_wikitext.lower()
    ]
    promo_terms = [
        term for term in PROMOTIONAL_TERMS if term.lower() in translated_wikitext.lower()
    ]

    if translated_plain_len > source_plain_len * 1.25 and translated_refs <= source_refs:
        risk_reasons.append("Large amount of possible new content without more references.")
        suggested_fixes.append("Remove unsourced additions or add reliable citations.")

    if external_links >= 20:
        risk_reasons.append(f"Large number of external links detected ({external_links}).")
        suggested_fixes.append("Keep only necessary, reliable external links and references.")

    if "[TRANSLATION PLACEHOLDER]" in translated_wikitext:
        risk_reasons.append("Placeholder / machine-translation marker still present.")
        suggested_fixes.append("Complete human translation and remove placeholder markers.")

    if korean_style_findings and target_lang.strip().lower() == "ko":
        risk_reasons.append("Korean draft still contains polite-style endings.")
        suggested_fixes.append("Revise Korean prose into encyclopedic style after proofreading.")

    if promo_terms:
        risk_reasons.append("Possible promotional or advertising wording detected.")
        suggested_fixes.append("Rewrite promotional language into neutral encyclopedic prose.")

    if suspicious_urls:
        risk_reasons.append("Suspicious or shortened URL pattern detected.")
        suggested_fixes.append("Replace questionable URLs with reliable, transparent sources.")

    if template_report["missing_templates"] or template_report["extra_templates"]:
        risk_reasons.append("Templates were added, removed, or disrupted.")
        suggested_fixes.append("Review template diffs and restore required templates.")

    if translated_refs < max(1, source_refs // 2):
        risk_reasons.append("Reference count appears too low compared with source.")
        suggested_fixes.append("Preserve source references and add citations for any new facts.")

    if not attribution_prepared:
        risk_reasons.append("No translation attribution / edit summary prepared.")
        suggested_fixes.append("Prepare a clear translation attribution edit summary.")

    if not human_proofreading_confirmed:
        risk_reasons.append("Human proofreading has not been confirmed.")
        suggested_fixes.append("Proofread in sandbox before attempting publication.")

    if len(risk_reasons) >= 6:
        risk_level = "high"
    elif len(risk_reasons) >= 3:
        risk_level = "medium"
    else:
        risk_level = "low"

    if risk_reasons:
        suggested_fixes.extend(
            [
                "Save and review the draft in a sandbox first.",
                "Split large, complex changes into easier-to-review edits when appropriate.",
                "Do not attempt to bypass edit filters; fix the underlying policy issues.",
            ]
        )

    return {
        "risk_level": risk_level,
        "risk_reasons": risk_reasons,
        "suggested_fixes": list(dict.fromkeys(suggested_fixes)),
        "signals": {
            "external_links_count": external_links,
            "suspicious_url_patterns": suspicious_urls,
            "promotional_terms": promo_terms,
            "korean_style_findings_count": len(korean_style_findings),
            "translated_ref_count": translated_refs,
            "translated_citation_template_count": citation_templates,
        },
    }


def build_final_publishing_checklist(
    translated_wikitext: str,
    template_report: dict[str, Any],
    reference_report: dict[str, Any],
    link_report: dict[str, Any],
    image_category_report: dict[str, Any],
    structure_report: dict[str, Any],
    talk_page_report: dict[str, Any],
    attribution_report: dict[str, Any],
    educational_report: dict[str, Any],
    page_move_report: dict[str, Any],
    edit_filter_report: dict[str, Any],
    target_lang: str,
    human_proofreading_confirmed: bool = False,
) -> list[dict[str, str]]:
    """Combine prior checks into a final manual publishing checklist."""
    korean_findings = check_korean_encyclopedic_style(translated_wikitext)
    link_summary = link_report["summary"]
    references_section = structure_report["references_section"]

    return [
        {
            "item": "Translation complete",
            "status": "missing" if "[TRANSLATION PLACEHOLDER]" in translated_wikitext else "manual",
            "detail": "Remove placeholder text and complete human-reviewed translation.",
        },
        {
            "item": "References preserved",
            "status": "passed" if not reference_report["issues"] else "needs_review",
            "detail": reference_report["summary"],
        },
        {
            "item": "No unsourced AI content",
            "status": "manual",
            "detail": "Manually confirm all added factual claims have reliable sources.",
        },
        {
            "item": "Templates checked",
            "status": "passed" if not template_report["warnings"] else "needs_review",
            "detail": f"{len(template_report['warnings'])} template warning(s).",
        },
        {
            "item": "Infobox checked",
            "status": "passed"
            if (
                not template_report["infobox_present_in_source"]
                or template_report["infobox_present_in_translation"]
            )
            else "missing",
            "detail": "Confirm infobox is preserved and localized when needed.",
        },
        {
            "item": "Korean encyclopedic style checked",
            "status": "passed"
            if target_lang.strip().lower() == "ko" and not korean_findings
            else "manual",
            "detail": (
                f"{len(korean_findings)} polite-style finding(s)."
                if target_lang.strip().lower() == "ko"
                else "Manual check required for target-language encyclopedic style."
            ),
        },
        {
            "item": "Blue links checked",
            "status": "passed" if link_summary["blue_links"] > 0 else "manual",
            "detail": f"{link_summary['blue_links']} blue link candidate(s).",
        },
        {
            "item": "Red links reviewed",
            "status": "needs_review" if link_summary["red_link_risks"] else "passed",
            "detail": f"{link_summary['red_link_risks']} red-link risk(s).",
        },
        {
            "item": "Images copyright reviewed",
            "status": "manual",
            "detail": f"{len(image_category_report['image_files_detected'])} image file(s) detected.",
        },
        {
            "item": "Categories added",
            "status": "passed" if image_category_report["translated_categories"] else "missing",
            "detail": f"{len(image_category_report['translated_categories'])} draft categor(ies).",
        },
        {
            "item": "References section exists",
            "status": "passed" if references_section["references_section_present"] else "missing",
            "detail": ", ".join(references_section["expected_headings"]),
        },
        {
            "item": "Talk page templates prepared",
            "status": "passed" if talk_page_report["copy_ready_talk_page_wikitext"] else "missing",
            "detail": "Place templates on talk page, not article page.",
        },
        {
            "item": "Translation attribution prepared",
            "status": "passed" if attribution_report["recommended_edit_summary"] else "missing",
            "detail": "Use the recommended edit summary or equivalent attribution.",
        },
        {
            "item": "Educational assignment prepared",
            "status": "manual" if educational_report["copy_ready_template"] else "missing",
            "detail": "Use only if the article is part of a course assignment.",
        },
        {
            "item": "Page move checklist reviewed",
            "status": "needs_review"
            if any(item["status"] in {"missing", "needs_review"} for item in page_move_report["checklist"])
            else "manual",
            "detail": "Move to mainspace manually when appropriate; do not copy-paste.",
        },
        {
            "item": "Edit filter risk reviewed",
            "status": "needs_review" if edit_filter_report["risk_level"] != "low" else "passed",
            "detail": f"Risk level: {edit_filter_report['risk_level']}.",
        },
        {
            "item": "Human proofreading completed",
            "status": "passed" if human_proofreading_confirmed else "manual",
            "detail": "Final publication requires human proofreading.",
        },
    ]
