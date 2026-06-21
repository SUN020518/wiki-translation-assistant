"""Wikipedia Translation Assistant — Streamlit app."""

from __future__ import annotations

import streamlit as st

from translator import PLACEHOLDER_MARKER, translate_text
from validator import (
    check_korean_encyclopedic_style,
    check_references,
    check_templates,
    validate_lang_code,
    validate_title,
)
from wiki_api import WikiAPIError, WikiArticleNotFoundError, fetch_wikitext

st.set_page_config(
    page_title="Wikipedia Translation Assistant",
    page_icon="🌐",
    layout="wide",
)

DISCLAIMER = (
    "**Important:** This tool is a translation *assistant* only. "
    "Do **not** publish machine-generated translations to Wikipedia without "
    "thorough human review. Automated or unreviewed AI translations may violate "
    "Wikipedia content policies and harm article quality."
)

REFERENCE_DISCLAIMER = (
    "**Reference policy reminder:** Do not add unsourced AI-generated content. "
    "On Wikipedia, all new factual statements must cite reliable sources. "
    "Publishing AI text without references may lead to article deletion or account sanctions."
)

MANUAL_REVIEW_NOTE = (
    "These checks are helpers only — they cannot replace careful human proofreading."
)


def _init_session_state() -> None:
    defaults = {
        "source_lang": "en",
        "target_lang": "ko",
        "article_title": "Alan Turing",
        "source_wikitext": "",
        "draft_wikitext": "",
        "fetch_error": "",
        "last_fetched_title": "",
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def _render_sidebar() -> None:
    st.sidebar.header("Settings")
    st.session_state.source_lang = st.sidebar.text_input(
        "Source language",
        value=st.session_state.source_lang,
        help='Wikipedia language code, e.g. "en".',
    )
    st.session_state.target_lang = st.sidebar.text_input(
        "Target language",
        value=st.session_state.target_lang,
        help='Target language code, e.g. "ko", "zh", "ja".',
    )
    st.session_state.article_title = st.sidebar.text_input(
        "Article title",
        value=st.session_state.article_title,
        help='Exact article title, e.g. "Alan Turing".',
    )


def _validate_inputs() -> tuple[str, str, str] | None:
    ok, source_lang = validate_lang_code(st.session_state.source_lang, "Source language")
    if not ok:
        st.error(source_lang)
        return None

    ok, target_lang = validate_lang_code(st.session_state.target_lang, "Target language")
    if not ok:
        st.error(target_lang)
        return None

    ok, title = validate_title(st.session_state.article_title)
    if not ok:
        st.error(title)
        return None

    return source_lang, target_lang, title


def _need_source_and_draft() -> bool:
    if not st.session_state.source_wikitext:
        st.warning("Fetch an article first on the **Fetch Article** tab.")
        return False
    if not st.session_state.draft_wikitext:
        st.warning("Generate a draft first on the **Translate Draft** tab.")
        return False
    return True


def _tab_fetch(source_lang: str, target_lang: str, title: str) -> None:
    st.subheader("Fetch Article")
    st.caption(
        f"Source: `{source_lang}.wikipedia.org` · "
        f"Target draft language: `{target_lang}` · "
        f'Title: "{title}"'
    )

    if st.button("Fetch wikitext", type="primary", key="fetch_btn"):
        with st.spinner("Fetching article from Wikipedia…"):
            try:
                wikitext = fetch_wikitext(source_lang, title)
                st.session_state.source_wikitext = wikitext
                st.session_state.draft_wikitext = ""
                st.session_state.fetch_error = ""
                st.session_state.last_fetched_title = title
                st.success(f'Loaded "{title}" ({len(wikitext):,} characters).')
            except WikiArticleNotFoundError as exc:
                st.session_state.source_wikitext = ""
                st.session_state.draft_wikitext = ""
                st.session_state.fetch_error = str(exc)
                st.error(str(exc))
            except WikiAPIError as exc:
                st.session_state.fetch_error = str(exc)
                st.error(str(exc))

    if st.session_state.fetch_error and not st.session_state.source_wikitext:
        st.info("Fix the title or language code, then try fetching again.")

    if st.session_state.source_wikitext:
        st.markdown("#### Source wikitext preview")
        st.text_area(
            "Source wikitext",
            value=st.session_state.source_wikitext,
            height=400,
            disabled=True,
            label_visibility="collapsed",
        )
        st.caption(
            f"Preview of `{st.session_state.last_fetched_title or title}` "
            f"({len(st.session_state.source_wikitext):,} characters)."
        )


def _tab_translate(source_lang: str, target_lang: str, title: str) -> None:
    st.subheader("Translate Draft")
    st.caption(
        f"MVP uses a placeholder translator (`{PLACEHOLDER_MARKER}`). "
        "Replace with human-reviewed translation before publishing."
    )

    if not st.session_state.source_wikitext:
        st.warning("Fetch an article first on the **Fetch Article** tab.")
        return

    if st.button("Generate draft translation", type="primary", key="translate_btn"):
        draft = translate_text(
            st.session_state.source_wikitext,
            source_lang,
            target_lang,
        )
        st.session_state.draft_wikitext = draft
        st.success("Draft translation generated (placeholder).")

    if st.session_state.draft_wikitext:
        st.markdown("#### Translated draft wikitext")
        st.text_area(
            "Draft wikitext",
            value=st.session_state.draft_wikitext,
            height=400,
            disabled=True,
            label_visibility="collapsed",
        )


def _tab_export() -> None:
    st.subheader("Export")
    st.warning(DISCLAIMER)

    if not st.session_state.draft_wikitext:
        st.info(
            "No draft available yet. Fetch an article and generate a draft on the "
            "**Translate Draft** tab."
        )
        return

    st.markdown("#### Copy-ready wikitext")
    st.code(st.session_state.draft_wikitext, language=None)
    st.download_button(
        label="Download draft as .wikitext",
        data=st.session_state.draft_wikitext,
        file_name="translation_draft.wikitext",
        mime="text/plain",
    )


def _tab_template_check() -> None:
    st.subheader("Template Check")
    st.info(MANUAL_REVIEW_NOTE)

    if not _need_source_and_draft():
        return

    report = check_templates(
        st.session_state.source_wikitext,
        st.session_state.draft_wikitext,
    )

    st.markdown("#### Summary")
    col1, col2, col3 = st.columns(3)
    col1.metric("Source templates", len(report["source_templates"]))
    col2.metric("Translation templates", len(report["translated_templates"]))
    col3.metric("Missing templates", len(report["missing_templates"]))

    c1, c2 = st.columns(2)
    c1.write(
        f"Infobox in source: **{'Yes' if report['infobox_present_in_source'] else 'No'}**"
    )
    c2.write(
        "Infobox in translation: "
        f"**{'Yes' if report['infobox_present_in_translation'] else 'No'}**"
    )
    c1, c2 = st.columns(2)
    c1.write(f"Citation templates (source): **{report['citation_templates_count_source']}**")
    c2.write(
        "Citation templates (translation): "
        f"**{report['citation_templates_count_translation']}**"
    )

    has_problems = (
        report["missing_templates"]
        or report["extra_templates"]
        or report["warnings"]
    )

    if not has_problems and not report["suggestions"]:
        st.success("Template check passed — no missing or extra templates detected.")
    elif not report["warnings"] and not report["missing_templates"]:
        st.success("Core templates appear preserved.")
    else:
        st.warning("Template differences found — review the details below.")

    if report["warnings"]:
        st.markdown("#### Warnings")
        for item in report["warnings"]:
            st.error(item)

    if report["suggestions"]:
        st.markdown("#### Suggestions")
        for item in report["suggestions"]:
            st.info(item)

    with st.expander("Detailed template lists"):
        st.markdown("**Missing in translation**")
        if report["missing_templates"]:
            for name in report["missing_templates"]:
                st.write(f"- `{name}`")
        else:
            st.write("None")

        st.markdown("**Extra in translation**")
        if report["extra_templates"]:
            for name in report["extra_templates"]:
                st.write(f"- `{name}`")
        else:
            st.write("None")

        st.markdown("**Unique source templates**")
        st.write(", ".join(f"`{n}`" for n in report["source_templates_unique"]) or "None")

        st.markdown("**Unique translation templates**")
        st.write(
            ", ".join(f"`{n}`" for n in report["translated_templates_unique"]) or "None"
        )


def _tab_reference_check() -> None:
    st.subheader("Reference Check")
    st.error(REFERENCE_DISCLAIMER)
    st.info(MANUAL_REVIEW_NOTE)

    if not _need_source_and_draft():
        return

    report = check_references(
        st.session_state.source_wikitext,
        st.session_state.draft_wikitext,
    )
    source_stats = report["source_stats"]
    translated_stats = report["translated_stats"]
    issues = report["issues"]

    st.markdown("#### Summary")
    st.caption(report["summary"])

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Source**")
        st.write(f"- `<ref>` tags: **{source_stats['ref_tag_count']}**")
        st.write(f"- Named refs: **{source_stats['named_ref_count']}**")
        st.write(f"- Self-closing refs: **{source_stats['self_closing_ref_count']}**")
        st.write(f"- Citation templates: **{source_stats['citation_template_count']}**")
    with col2:
        st.markdown("**Translation**")
        st.write(f"- `<ref>` tags: **{translated_stats['ref_tag_count']}**")
        st.write(f"- Named refs: **{translated_stats['named_ref_count']}**")
        st.write(f"- Self-closing refs: **{translated_stats['self_closing_ref_count']}**")
        st.write(
            f"- Citation templates: **{translated_stats['citation_template_count']}**"
        )

    errors = [i for i in issues if i["severity"] == "error"]
    warnings = [i for i in issues if i["severity"] == "warning"]
    infos = [i for i in issues if i["severity"] == "info"]

    if not issues:
        st.success("Reference check passed — no obvious alignment issues found.")
    else:
        if errors:
            st.error(f"{len(errors)} critical reference issue(s) found.")
        if warnings:
            st.warning(f"{len(warnings)} reference warning(s) found.")
        if infos and not errors and not warnings:
            st.info("Minor reference notes — review below.")

    st.markdown("#### Metadata preservation")
    for field, data in report["metadata_alignment"].items():
        label = field.replace("-", " ").title()
        if data["source_count"] == 0:
            continue
        if data["preserved"]:
            st.success(
                f"{label}: source {data['source_count']} → translation "
                f"{data['translated_count']}"
            )
        else:
            st.warning(
                f"{label}: source {data['source_count']} → translation "
                f"{data['translated_count']} (possible loss)"
            )

    if issues:
        st.markdown("#### Issues")
        for item in issues:
            severity = item["severity"]
            message = f"**{item['issue']}** — {item['detail']}"
            if severity == "error":
                st.error(message)
            elif severity == "warning":
                st.warning(message)
            else:
                st.info(message)


def _tab_korean_style_check(target_lang: str) -> None:
    st.subheader("Korean Style Check")
    st.info(
        "Korean Wikipedia prefers encyclopedic style (**이다体**: ~이다, ~한다) over "
        "formal polite style (~입니다, ~합니다). This check flags likely machine-translation "
        "patterns for manual review."
    )
    st.info(MANUAL_REVIEW_NOTE)

    if target_lang != "ko":
        st.warning(
            f'Target language is "{target_lang}", not Korean (`ko`). '
            "This check is designed for Korean Wikipedia drafts."
        )

    if not st.session_state.draft_wikitext:
        st.warning("Generate a draft first on the **Translate Draft** tab.")
        return

    findings = check_korean_encyclopedic_style(st.session_state.draft_wikitext)

    st.markdown("#### Summary")
    if not findings:
        st.success(
            "No formal/polite Korean endings detected — draft looks compatible with "
            "encyclopedic style (or contains no Korean text)."
        )
    else:
        unique_phrases = sorted({f["problematic_phrase"] for f in findings})
        st.warning(
            f"Found **{len(findings)}** occurrence(s) of **{len(unique_phrases)}** "
            "problematic phrase type(s). Review each suggestion manually — do not auto-replace."
        )

    if findings:
        st.markdown("#### Detailed findings")
        for item in findings:
            st.warning(
                f'Line **{item["line_number"]}**, position ~{item["approximate_position"]}: '
                f'`{item["problematic_phrase"]}` → suggest `{item["suggestion"]}`'
            )
            st.caption(f'Context: {item["context"]}')


def main() -> None:
    _init_session_state()

    st.title("Wikipedia Translation Assistant")
    st.markdown(
        "Fetch Wikipedia source wikitext, generate a draft translation, run quality checks, "
        "and export for manual review."
    )
    st.info(DISCLAIMER)

    _render_sidebar()

    validated = _validate_inputs()
    if validated is None:
        st.stop()

    source_lang, target_lang, title = validated

    (
        tab_fetch,
        tab_translate,
        tab_export,
        tab_template,
        tab_reference,
        tab_korean,
    ) = st.tabs(
        [
            "Fetch Article",
            "Translate Draft",
            "Export",
            "Template Check",
            "Reference Check",
            "Korean Style Check",
        ]
    )

    with tab_fetch:
        _tab_fetch(source_lang, target_lang, title)

    with tab_translate:
        _tab_translate(source_lang, target_lang, title)

    with tab_export:
        _tab_export()

    with tab_template:
        _tab_template_check()

    with tab_reference:
        _tab_reference_check()

    with tab_korean:
        _tab_korean_style_check(target_lang)


if __name__ == "__main__":
    main()
