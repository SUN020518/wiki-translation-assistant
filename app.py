"""Wikipedia Translation Assistant — editorial review UI."""

from __future__ import annotations

import streamlit as st

from translator import PLACEHOLDER_MARKER, translate_text
from validator import (
    check_images_and_categories,
    check_korean_encyclopedic_style,
    check_links,
    check_references,
    check_templates,
    check_wiki_structure,
    validate_lang_code,
    validate_title,
)
from wiki_api import (
    WikiAPIError,
    WikiArticleNotFoundError,
    check_pages_status,
    fetch_wikitext,
    get_language_link_candidates,
)

st.set_page_config(
    page_title="Wikipedia Translation Assistant",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)

PHASE_LABEL = "Phase 3 — Link & Wiki Structure Checks"

DISCLAIMER = (
    "This tool is a translation assistant only. Do not publish machine-generated "
    "translations to Wikipedia without thorough human review."
)

REFERENCE_DISCLAIMER = (
    "Do not add unsourced AI-generated content. On Wikipedia, all new factual "
    "statements must cite reliable sources. Publishing AI text without references "
    "may lead to article deletion or account sanctions."
)

MANUAL_REVIEW_NOTE = (
    "These checks are helpers only — they cannot replace careful human proofreading."
)

WIKI_STYLES = """
<style>
    /* Light editorial workspace — distinct from dark dashboard / casino UIs */
    .stApp {
        background-color: #f3f4f6;
    }

    [data-testid="stSidebar"] {
        background-color: #ffffff;
        border-right: 1px solid #e5e7eb;
    }

    [data-testid="stSidebar"] .block-container {
        padding-top: 1.5rem;
    }

    .wiki-doc-header {
        background: #ffffff;
        border: 1px solid #e5e7eb;
        border-left: 4px solid #3366cc;
        border-radius: 8px;
        padding: 1.25rem 1.5rem;
        margin-bottom: 1rem;
        box-shadow: 0 1px 3px rgba(15, 23, 42, 0.06);
    }

    .wiki-doc-header h1 {
        color: #202122;
        font-size: 1.65rem;
        font-weight: 700;
        margin: 0 0 0.35rem 0;
        line-height: 1.3;
    }

    .wiki-doc-header .wiki-subtitle {
        color: #54595d;
        font-size: 1rem;
        margin: 0 0 0.75rem 0;
        line-height: 1.5;
    }

    .wiki-phase-badge {
        display: inline-block;
        background: #eaf3ff;
        color: #3366cc;
        border: 1px solid #c8daf5;
        border-radius: 999px;
        padding: 0.2rem 0.75rem;
        font-size: 0.82rem;
        font-weight: 600;
        letter-spacing: 0.01em;
    }

    .wiki-intro-panel {
        background: #ffffff;
        border: 1px solid #e5e7eb;
        border-radius: 8px;
        padding: 1rem 1.25rem;
        margin-bottom: 1.25rem;
        box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
    }

    .wiki-intro-panel h3 {
        color: #202122;
        font-size: 0.95rem;
        font-weight: 700;
        margin: 0 0 0.65rem 0;
    }

    .wiki-intro-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
        gap: 0.75rem;
    }

    .wiki-intro-item {
        background: #f8f9fa;
        border: 1px solid #eaecf0;
        border-radius: 6px;
        padding: 0.75rem 0.9rem;
    }

    .wiki-intro-item strong {
        display: block;
        color: #202122;
        font-size: 0.88rem;
        margin-bottom: 0.25rem;
    }

    .wiki-intro-item span {
        color: #54595d;
        font-size: 0.84rem;
        line-height: 1.45;
    }

    .wiki-section-card {
        background: #ffffff;
        border: 1px solid #e5e7eb;
        border-radius: 8px;
        padding: 1rem 1.15rem;
        margin-bottom: 1rem;
        box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
    }

    .wiki-section-title {
        color: #202122;
        font-size: 1.05rem;
        font-weight: 700;
        margin: 0 0 0.35rem 0;
        padding-bottom: 0.45rem;
        border-bottom: 1px solid #eaecf0;
    }

    .wiki-section-caption {
        color: #72777d;
        font-size: 0.86rem;
        margin: 0 0 0.85rem 0;
        line-height: 1.45;
    }

    .wiki-summary-row {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
        gap: 0.75rem;
        margin-bottom: 1rem;
    }

    .wiki-summary-card {
        background: #ffffff;
        border: 1px solid #e5e7eb;
        border-radius: 8px;
        padding: 0.85rem 1rem;
        box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
    }

    .wiki-summary-card .label {
        color: #72777d;
        font-size: 0.78rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.03em;
        margin-bottom: 0.25rem;
    }

    .wiki-summary-card .value {
        color: #202122;
        font-size: 1.45rem;
        font-weight: 700;
        line-height: 1.2;
    }

    .wiki-summary-card .note {
        color: #54595d;
        font-size: 0.8rem;
        margin-top: 0.25rem;
    }

    .wiki-status {
        display: inline-flex;
        align-items: center;
        gap: 0.35rem;
        border-radius: 6px;
        padding: 0.45rem 0.75rem;
        font-size: 0.88rem;
        font-weight: 600;
        margin: 0.35rem 0 0.75rem 0;
        line-height: 1.4;
    }

    .wiki-status-pass {
        background: #ecfdf3;
        color: #067647;
        border: 1px solid #abefc6;
    }

    .wiki-status-warn {
        background: #fffaeb;
        color: #b54708;
        border: 1px solid #fedf89;
    }

    .wiki-status-error {
        background: #fef3f2;
        color: #b42318;
        border: 1px solid #fecdca;
    }

    .wiki-status-info {
        background: #eff8ff;
        color: #175cd3;
        border: 1px solid #b2ddff;
    }

    .wiki-safety-box {
        background: #fff8e6;
        border: 1px solid #f0d899;
        border-radius: 6px;
        padding: 0.75rem 0.9rem;
        color: #5c4a00;
        font-size: 0.84rem;
        line-height: 1.45;
        margin-top: 0.75rem;
    }

    .wiki-safety-box strong {
        color: #3d3200;
    }

    .wiki-muted {
        color: #72777d;
        font-size: 0.84rem;
    }

    div[data-testid="stTabs"] button[data-baseweb="tab"] {
        font-weight: 600;
    }

    @media (max-width: 768px) {
        .wiki-doc-header h1 {
            font-size: 1.35rem;
        }

        .wiki-doc-header .wiki-subtitle {
            font-size: 0.92rem;
        }

        .wiki-summary-row {
            grid-template-columns: repeat(2, minmax(0, 1fr));
        }
    }
</style>
"""


def _inject_styles() -> None:
    st.markdown(WIKI_STYLES, unsafe_allow_html=True)


def _status_badge(level: str, message: str) -> None:
    css_class = {
        "pass": "wiki-status-pass",
        "warning": "wiki-status-warn",
        "error": "wiki-status-error",
        "info": "wiki-status-info",
    }.get(level, "wiki-status-info")
    icon = {
        "pass": "✅ Passed",
        "warning": "⚠️ Warning",
        "error": "❌ Needs review",
        "info": "ℹ️ Info",
    }.get(level, "ℹ️ Info")
    st.markdown(
        f'<div class="wiki-status {css_class}">{icon} — {message}</div>',
        unsafe_allow_html=True,
    )


def _summary_cards(cards: list[tuple[str, str, str]]) -> None:
    html_parts = ['<div class="wiki-summary-row">']
    for label, value, note in cards:
        html_parts.append(
            f"""
            <div class="wiki-summary-card">
                <div class="label">{label}</div>
                <div class="value">{value}</div>
                <div class="note">{note}</div>
            </div>
            """
        )
    html_parts.append("</div>")
    st.markdown("".join(html_parts), unsafe_allow_html=True)


def _section(title: str, caption: str = "") -> None:
    caption_html = f'<p class="wiki-section-caption">{caption}</p>' if caption else ""
    st.markdown(
        f"""
        <div class="wiki-section-card">
            <div class="wiki-section-title">{title}</div>
            {caption_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_header() -> None:
    st.markdown(
        f"""
        <div class="wiki-doc-header">
            <h1>Wikipedia Translation Assistant</h1>
            <p class="wiki-subtitle">
                Draft translation, citation checks, link review, structure checks, and publishing guidance
            </p>
            <span class="wiki-phase-badge">{PHASE_LABEL}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_intro_panel() -> None:
    st.markdown(
        """
        <div class="wiki-intro-panel">
            <h3>Editorial workflow overview</h3>
            <div class="wiki-intro-grid">
                <div class="wiki-intro-item">
                    <strong>What this tool does</strong>
                    <span>
                        Fetches Wikipedia wikitext, prepares a translation draft, and runs
                        template, reference, link, media, category, and style checks.
                    </span>
                </div>
                <div class="wiki-intro-item">
                    <strong>What this tool does not do</strong>
                    <span>
                        It does not log in to Wikipedia, edit pages, or publish content
                        automatically. You remain responsible for every submission.
                    </span>
                </div>
                <div class="wiki-intro-item">
                    <strong>Human review required</strong>
                    <span>
                        All machine-assisted output must be proofread, corrected, and verified
                        against reliable sources before publishing.
                    </span>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
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
        "sidebar_validation_error": "",
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def _validate_inputs() -> tuple[str, str, str] | None:
    ok, source_lang = validate_lang_code(st.session_state.source_lang, "Source language")
    if not ok:
        st.session_state.sidebar_validation_error = source_lang
        return None

    ok, target_lang = validate_lang_code(st.session_state.target_lang, "Target language")
    if not ok:
        st.session_state.sidebar_validation_error = target_lang
        return None

    ok, title = validate_title(st.session_state.article_title)
    if not ok:
        st.session_state.sidebar_validation_error = title
        return None

    st.session_state.sidebar_validation_error = ""
    return source_lang, target_lang, title


def _render_sidebar() -> tuple[str, str, str] | None:
    st.sidebar.markdown("### Project controls")
    st.sidebar.caption("Configure languages and article, then run fetch and draft steps.")

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

    validated = _validate_inputs()
    if validated is None:
        st.sidebar.error(st.session_state.sidebar_validation_error)
        st.sidebar.markdown(
            '<div class="wiki-safety-box"><strong>Safety reminder:</strong> '
            "Fix the inputs above before fetching or generating a draft.</div>",
            unsafe_allow_html=True,
        )
        return None

    source_lang, target_lang, title = validated

    st.sidebar.markdown("---")
    st.sidebar.markdown("**Workflow actions**")

    if st.sidebar.button("Fetch article", type="primary", use_container_width=True):
        with st.spinner("Fetching wikitext…"):
            try:
                wikitext = fetch_wikitext(source_lang, title)
                st.session_state.source_wikitext = wikitext
                st.session_state.draft_wikitext = ""
                st.session_state.fetch_error = ""
                st.session_state.last_fetched_title = title
                st.sidebar.success(f'Loaded "{title}".')
            except WikiArticleNotFoundError as exc:
                st.session_state.source_wikitext = ""
                st.session_state.draft_wikitext = ""
                st.session_state.fetch_error = str(exc)
                st.sidebar.error(str(exc))
            except WikiAPIError as exc:
                st.session_state.fetch_error = str(exc)
                st.sidebar.error(str(exc))

    if st.sidebar.button("Generate draft", use_container_width=True):
        if not st.session_state.source_wikitext:
            st.sidebar.warning("Fetch an article before generating a draft.")
        else:
            draft = translate_text(
                st.session_state.source_wikitext,
                source_lang,
                target_lang,
            )
            st.session_state.draft_wikitext = draft
            st.sidebar.success("Draft generated (placeholder).")

    st.sidebar.markdown("---")
    st.sidebar.markdown("**Session status**")
    if st.session_state.source_wikitext:
        st.sidebar.write(
            f"Source loaded: **{st.session_state.last_fetched_title or title}** "
            f"({len(st.session_state.source_wikitext):,} chars)"
        )
    else:
        st.sidebar.write("Source loaded: **No**")

    st.sidebar.write(
        "Draft ready: **Yes**"
        if st.session_state.draft_wikitext
        else "Draft ready: **No**"
    )

    st.sidebar.markdown(
        '<div class="wiki-safety-box"><strong>Safety reminder:</strong> '
        "Never publish unreviewed AI translations. All new statements need reliable "
        "references. This tool does not post to Wikipedia.</div>",
        unsafe_allow_html=True,
    )

    return source_lang, target_lang, title


def _need_source() -> bool:
    if not st.session_state.source_wikitext:
        _status_badge("warning", "Fetch an article using the sidebar controls first.")
        return False
    return True


def _need_source_and_draft() -> bool:
    if not _need_source():
        return False
    if not st.session_state.draft_wikitext:
        _status_badge("warning", "Generate a draft using the sidebar controls first.")
        return False
    return True


@st.cache_data(show_spinner=False)
def _build_link_report(
    source_wikitext: str,
    source_lang: str,
    target_lang: str,
) -> dict:
    """Build and cache link report because page-status API checks can be slow."""
    preliminary = check_links(
        source_wikitext,
        source_lang,
        target_lang,
    )
    source_targets = [
        link["target"] for link in preliminary["source_internal_links"]
    ]
    candidates = get_language_link_candidates(source_lang, source_targets, target_lang)
    target_titles = [
        candidates.get(target, target)
        for target in source_targets
    ]
    statuses = check_pages_status(target_lang, target_titles)
    return check_links(
        source_wikitext,
        source_lang,
        target_lang,
        target_page_candidates=candidates,
        target_page_statuses=statuses,
    )


def _tab_article_source(source_lang: str, target_lang: str, title: str) -> None:
    _section(
        "Article Source",
        f"Review wikitext fetched from {source_lang}.wikipedia.org before translation.",
    )

    st.markdown(
        f'<p class="wiki-muted">Target draft language: <strong>{target_lang}</strong> · '
        f'Article: <strong>{title}</strong></p>',
        unsafe_allow_html=True,
    )

    if st.session_state.fetch_error and not st.session_state.source_wikitext:
        _status_badge("error", st.session_state.fetch_error)
        st.info("Adjust the sidebar inputs and click **Fetch article** to try again.")

    if st.session_state.source_wikitext:
        _status_badge(
            "pass",
            f'Source loaded — "{st.session_state.last_fetched_title or title}" '
            f"({len(st.session_state.source_wikitext):,} characters).",
        )
        st.markdown("##### Wikitext preview")
        st.text_area(
            "Source wikitext",
            value=st.session_state.source_wikitext,
            height=420,
            disabled=True,
            label_visibility="collapsed",
        )
    elif not st.session_state.fetch_error:
        _status_badge("info", "No article loaded yet. Use the sidebar to fetch wikitext.")


def _tab_translation_draft(source_lang: str, target_lang: str) -> None:
    _section(
        "Translation Draft",
        f"Placeholder draft for {source_lang} → {target_lang}. Replace with human-reviewed text.",
    )

    if not _need_source():
        return

    st.markdown(
        f'<p class="wiki-muted">Draft mode: placeholder marker '
        f"<code>{PLACEHOLDER_MARKER}</code></p>",
        unsafe_allow_html=True,
    )

    if st.session_state.draft_wikitext:
        _status_badge("pass", "Draft available for review and compliance checks.")
        st.markdown("##### Draft wikitext preview")
        st.text_area(
            "Draft wikitext",
            value=st.session_state.draft_wikitext,
            height=420,
            disabled=True,
            label_visibility="collapsed",
        )
    else:
        _status_badge(
            "info",
            "No draft yet. Click **Generate draft** in the sidebar after fetching the source.",
        )


def _tab_template_check() -> None:
    _section(
        "Template Check",
        "Compare templates between source and translation without modifying wikitext.",
    )
    st.caption(MANUAL_REVIEW_NOTE)

    if not _need_source_and_draft():
        return

    report = check_templates(
        st.session_state.source_wikitext,
        st.session_state.draft_wikitext,
    )

    infobox_status = "Present" if report["infobox_present_in_translation"] else "Missing"
    if report["infobox_present_in_source"] and not report["infobox_present_in_translation"]:
        infobox_status = "Missing (was in source)"

    _summary_cards(
        [
            ("Source templates", str(len(report["source_templates"])), "Total occurrences"),
            (
                "Translated templates",
                str(len(report["translated_templates"])),
                "Total occurrences",
            ),
            ("Missing templates", str(len(report["missing_templates"])), "In source only"),
            ("Infobox status", infobox_status, "Translation draft"),
        ]
    )

    has_problems = (
        report["missing_templates"]
        or report["extra_templates"]
        or report["warnings"]
    )

    if not has_problems and not report["suggestions"]:
        _status_badge("pass", "No missing or extra templates detected.")
    elif not report["warnings"] and not report["missing_templates"]:
        _status_badge("pass", "Core templates appear preserved.")
    else:
        _status_badge("warning", "Template differences found — review details below.")

    st.markdown("##### Citation templates")
    st.write(
        f"Source: **{report['citation_templates_count_source']}** · "
        f"Translation: **{report['citation_templates_count_translation']}**"
    )

    if report["warnings"]:
        st.markdown("##### Warnings")
        for item in report["warnings"]:
            _status_badge("error", item)

    if report["suggestions"]:
        st.markdown("##### Suggestions")
        for item in report["suggestions"]:
            _status_badge("info", item)

    st.markdown("##### Detailed template lists")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Missing in translation**")
        if report["missing_templates"]:
            for name in report["missing_templates"]:
                st.write(f"- `{name}`")
        else:
            st.write("None")
    with col2:
        st.markdown("**Extra in translation**")
        if report["extra_templates"]:
            for name in report["extra_templates"]:
                st.write(f"- `{name}`")
        else:
            st.write("None")

    with st.expander("View unique template names"):
        st.markdown("**Source (unique)**")
        st.write(", ".join(f"`{n}`" for n in report["source_templates_unique"]) or "None")
        st.markdown("**Translation (unique)**")
        st.write(
            ", ".join(f"`{n}`" for n in report["translated_templates_unique"]) or "None"
        )


def _tab_reference_check() -> None:
    _section(
        "Reference Check",
        "Verify refs, named refs, and bibliographic metadata are preserved in the draft.",
    )
    _status_badge("error", REFERENCE_DISCLAIMER)
    st.caption(MANUAL_REVIEW_NOTE)

    if not _need_source_and_draft():
        return

    report = check_references(
        st.session_state.source_wikitext,
        st.session_state.draft_wikitext,
    )
    source_stats = report["source_stats"]
    translated_stats = report["translated_stats"]
    issues = report["issues"]

    _summary_cards(
        [
            ("Source refs", str(source_stats["ref_tag_count"]), "<ref> tags"),
            ("Translated refs", str(translated_stats["ref_tag_count"]), "<ref> tags"),
            ("Named refs", str(translated_stats["named_ref_count"]), "In translation"),
            (
                "Citation templates",
                str(translated_stats["citation_template_count"]),
                "In translation",
            ),
        ]
    )

    errors = [i for i in issues if i["severity"] == "error"]
    warnings = [i for i in issues if i["severity"] == "warning"]

    if not issues:
        _status_badge("pass", report["summary"])
    else:
        if errors:
            _status_badge(
                "error",
                f"{len(errors)} critical reference issue(s) require review.",
            )
        elif warnings:
            _status_badge("warning", f"{len(warnings)} reference warning(s) found.")
        else:
            _status_badge("info", report["summary"])

    st.markdown("##### Source vs. translation counts")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Source**")
        st.write(f"- Named refs: **{source_stats['named_ref_count']}**")
        st.write(f"- Self-closing refs: **{source_stats['self_closing_ref_count']}**")
        st.write(f"- Citation templates: **{source_stats['citation_template_count']}**")
    with col2:
        st.markdown("**Translation**")
        st.write(f"- Named refs: **{translated_stats['named_ref_count']}**")
        st.write(f"- Self-closing refs: **{translated_stats['self_closing_ref_count']}**")
        st.write(
            f"- Citation templates: **{translated_stats['citation_template_count']}**"
        )

    st.markdown("##### Metadata preservation")
    for field, data in report["metadata_alignment"].items():
        label = field.replace("-", " ").title()
        if data["source_count"] == 0:
            continue
        if data["preserved"]:
            _status_badge(
                "pass",
                f"{label}: {data['source_count']} → {data['translated_count']}",
            )
        else:
            _status_badge(
                "warning",
                f"{label}: {data['source_count']} → {data['translated_count']} (possible loss)",
            )

    if issues:
        st.markdown("##### Warning list")
        for item in issues:
            severity = item["severity"]
            message = f"{item['issue']} — {item['detail']}"
            if severity == "error":
                _status_badge("error", message)
            elif severity == "warning":
                _status_badge("warning", message)
            else:
                _status_badge("info", message)


def _tab_korean_style_check(target_lang: str) -> None:
    _section(
        "Korean Style Check",
        "Flag formal/polite endings (~입니다, ~합니다) that may not fit Korean Wikipedia style.",
    )
    st.caption(MANUAL_REVIEW_NOTE)

    if target_lang != "ko":
        _status_badge(
            "warning",
            f'Target language is "{target_lang}", not Korean (ko). '
            "This check is intended for Korean Wikipedia drafts.",
        )

    if not st.session_state.draft_wikitext:
        _status_badge("warning", "Generate a draft using the sidebar controls first.")
        return

    findings = check_korean_encyclopedic_style(st.session_state.draft_wikitext)

    if not findings:
        _status_badge(
            "pass",
            "No formal/polite Korean endings detected — compatible with encyclopedic style "
            "(or no Korean text present).",
        )
    else:
        unique_phrases = sorted({f["problematic_phrase"] for f in findings})
        _status_badge(
            "warning",
            f"Found {len(findings)} occurrence(s) across {len(unique_phrases)} phrase type(s). "
            "Review suggestions manually — do not auto-replace.",
        )

        st.markdown("##### Polite style phrases")
        table_rows = [
            {
                "Problem phrase": item["problematic_phrase"],
                "Line / position": f"Line {item['line_number']}, ~col {item['approximate_position']}",
                "Suggested encyclopedic form": item["suggestion"],
                "Context": item["context"],
            }
            for item in findings
        ]
        st.dataframe(table_rows, use_container_width=True, hide_index=True)


def _tab_link_check(source_lang: str, target_lang: str) -> None:
    _section(
        "Link Check",
        "Review internal links, blue-link availability, red-link risk, and temporary link suggestions.",
    )
    st.caption(MANUAL_REVIEW_NOTE)

    if not _need_source():
        return

    _status_badge(
        "info",
        "This report suggests link targets only. It does not rewrite article text automatically.",
    )

    try:
        with st.spinner("Checking target-language page availability…"):
            report = _build_link_report(
                st.session_state.source_wikitext,
                source_lang,
                target_lang,
            )
    except WikiAPIError as exc:
        _status_badge("error", f"Could not complete link API checks: {exc}")
        return

    summary = report["summary"]
    _summary_cards(
        [
            ("Internal links", str(summary["total_internal_links"]), "Source article"),
            ("Blue links", str(summary["blue_links"]), "Target page exists"),
            ("Red link risk", str(summary["red_link_risks"]), "Needs review"),
            ("Unknown", str(summary["unknown"]), "Could not verify"),
        ]
    )

    if summary["red_link_risks"] == 0 and summary["unknown"] == 0:
        _status_badge("pass", "No red-link risks found in checked target pages.")
    else:
        _status_badge(
            "warning",
            "Some links may need manual handling before publication.",
        )

    st.markdown("##### Temporary link template suggestion")
    st.write(
        f"For target language `{target_lang}`, consider: "
        f"`{report['temporary_link_template_suggestion']}`"
    )

    rows = [
        {
            "Source link": row["source_link"],
            "Display text": row["display_text"] or "",
            "Target candidate": row["target_page_candidate"],
            "Status": row["status"],
            "Suggestion": row["suggestion"],
        }
        for row in report["blue_link_alignment_report"]
    ]

    st.markdown("##### Detailed link report")
    if rows:
        st.dataframe(rows, use_container_width=True, hide_index=True)
    else:
        _status_badge("info", "No regular internal article links detected.")

    if report["disambiguation_warnings"]:
        st.markdown("##### Disambiguation warnings")
        for warning in report["disambiguation_warnings"]:
            _status_badge(
                "warning",
                f"{warning['target_page_candidate']} may be a disambiguation page. "
                f"{warning['suggestion']}",
            )


def _tab_image_category_check() -> None:
    _section(
        "Image & Category Check",
        "Review media links, copyright cautions, and target-wiki category presence.",
    )
    st.caption(MANUAL_REVIEW_NOTE)

    if not _need_source_and_draft():
        return

    report = check_images_and_categories(
        st.session_state.source_wikitext,
        st.session_state.draft_wikitext,
    )

    _summary_cards(
        [
            (
                "Image files",
                str(len(report["image_files_detected"])),
                "Detected in source",
            ),
            (
                "Source categories",
                str(len(report["source_categories"])),
                "Source article",
            ),
            (
                "Draft categories",
                str(len(report["translated_categories"])),
                "Translation draft",
            ),
            (
                "Category status",
                "Review" if report["missing_categories_warning"] else "Present",
                "Manual check",
            ),
        ]
    )

    st.markdown("##### Copyright and fair-use warnings")
    for warning in report["copyright_warnings"]:
        _status_badge("warning", warning)

    st.markdown("##### Detected image files")
    if report["image_files_detected"]:
        st.dataframe(
            report["image_files_detected"],
            use_container_width=True,
            hide_index=True,
        )
    else:
        _status_badge("info", "No File:/Image: wikilinks detected in the source article.")

    st.markdown("##### Categories")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Source categories**")
        if report["source_categories"]:
            for category in report["source_categories"]:
                st.write(f"- `{category}`")
        else:
            st.write("None detected")
    with col2:
        st.markdown("**Draft categories**")
        if report["translated_categories"]:
            for category in report["translated_categories"]:
                st.write(f"- `{category}`")
        else:
            st.write("None detected")

    if report["missing_categories_warning"]:
        _status_badge("warning", report["missing_categories_warning"])
    else:
        _status_badge(
            "pass",
            "Categories are present in the translation draft. Confirm they are blue-linked on the target wiki.",
        )

    _status_badge(
        "info",
        "Do not create categories automatically. Red-linked categories require manual handling.",
    )


def _tab_structure_check(source_lang: str, target_lang: str) -> None:
    _section(
        "Structure Check",
        "Check references section status, disambiguation warnings, and publishing structure reminders.",
    )
    st.caption(MANUAL_REVIEW_NOTE)

    if not _need_source_and_draft():
        return

    disambiguation_warnings: list[dict] = []
    try:
        with st.spinner("Refreshing link disambiguation checks…"):
            link_report = _build_link_report(
                st.session_state.source_wikitext,
                source_lang,
                target_lang,
            )
            disambiguation_warnings = link_report["disambiguation_warnings"]
    except WikiAPIError as exc:
        _status_badge("warning", f"Could not refresh disambiguation checks: {exc}")

    report = check_wiki_structure(
        st.session_state.draft_wikitext,
        target_lang,
        disambiguation_warnings,
    )
    references_section = report["references_section"]

    _summary_cards(
        [
            (
                "References section",
                "Present" if references_section["references_section_present"] else "Missing",
                f"Expected: {', '.join(references_section['expected_headings'])}",
            ),
            (
                "Headings found",
                str(len(references_section["headings_detected"])),
                "Draft structure",
            ),
            (
                "Disambiguation warnings",
                str(len(report["disambiguation_warnings"])),
                "Possible issues",
            ),
            ("Publishing mode", "Manual", "No auto-publish"),
        ]
    )

    if references_section["references_section_present"]:
        _status_badge("pass", "Expected references section heading detected.")
    else:
        _status_badge(
            "warning",
            references_section["missing_references_section_warning"],
        )

    if references_section["headings_detected"]:
        st.markdown("##### Headings detected")
        for heading in references_section["headings_detected"]:
            st.write(f"- `{heading}`")

    st.markdown("##### Disambiguation warnings")
    if report["disambiguation_warnings"]:
        for warning in report["disambiguation_warnings"]:
            _status_badge(
                "warning",
                f"{warning['target_page_candidate']} may be a disambiguation page. "
                f"{warning['suggestion']}",
            )
    else:
        _status_badge("pass", "No possible disambiguation pages detected in checked links.")

    st.markdown("##### Publishing structure reminders")
    for reminder in report["publishing_structure_reminders"]:
        _status_badge("info", reminder)


def _tab_export() -> None:
    _section(
        "Export",
        "Copy or download reviewed wikitext. Publishing remains a manual step on Wikipedia.",
    )

    _status_badge("info", "This tool does not publish to Wikipedia automatically.")
    _status_badge("warning", DISCLAIMER)

    if not st.session_state.draft_wikitext:
        _status_badge(
            "info",
            "No draft available yet. Fetch an article and generate a draft from the sidebar.",
        )
        return

    st.markdown("##### Copy-ready wikitext")
    st.code(st.session_state.draft_wikitext, language=None)

    st.download_button(
        label="Download draft as .wikitext",
        data=st.session_state.draft_wikitext,
        file_name="translation_draft.wikitext",
        mime="text/plain",
        use_container_width=False,
    )

    st.markdown(
        '<div class="wiki-safety-box"><strong>Publishing safety reminder:</strong> '
        "Export is for manual copy into your editor or Wikipedia sandbox. Verify templates, "
        "references, and prose quality before any submission. Unsourced AI content violates "
        "Wikipedia policy.</div>",
        unsafe_allow_html=True,
    )


def _tab_about() -> None:
    _section(
        "About",
        "Documentation for editors using this translation review assistant.",
    )

    st.markdown(
        f"""
**Current release:** {PHASE_LABEL}

**Workflow**
1. Fetch source wikitext from Wikipedia.
2. Generate a translation draft (placeholder in current version).
3. Run template, reference, link, media, category, structure, and Korean style checks.
4. Export and complete human proofreading before publishing.

**Policy reminders**
- This is an editorial assistant, not an auto-publishing bot.
- Do not submit unreviewed machine translations.
- All new factual content must cite reliable sources.
- Automated checks cannot replace human proofreading.

**Modules**
- `wiki_api.py` — fetch wikitext via MediaWiki API
- `translator.py` — draft generation (placeholder)
- `validator.py` — input validation and compliance checkers
        """
    )


def main() -> None:
    _init_session_state()
    _inject_styles()

    validated = _render_sidebar()
    if validated is None:
        _render_header()
        _render_intro_panel()
        st.warning("Correct the sidebar inputs to continue.")
        st.stop()

    source_lang, target_lang, title = validated

    _render_header()
    _render_intro_panel()

    (
        tab_source,
        tab_draft,
        tab_template,
        tab_reference,
        tab_korean,
        tab_link,
        tab_image_category,
        tab_structure,
        tab_export,
        tab_about,
    ) = st.tabs(
        [
            "Article Source",
            "Translation Draft",
            "Template Check",
            "Reference Check",
            "Korean Style Check",
            "Link Check",
            "Image & Category Check",
            "Structure Check",
            "Export",
            "About",
        ]
    )

    with tab_source:
        _tab_article_source(source_lang, target_lang, title)

    with tab_draft:
        _tab_translation_draft(source_lang, target_lang)

    with tab_template:
        _tab_template_check()

    with tab_reference:
        _tab_reference_check()

    with tab_korean:
        _tab_korean_style_check(target_lang)

    with tab_link:
        _tab_link_check(source_lang, target_lang)

    with tab_image_category:
        _tab_image_category_check()

    with tab_structure:
        _tab_structure_check(source_lang, target_lang)

    with tab_export:
        _tab_export()

    with tab_about:
        _tab_about()


if __name__ == "__main__":
    main()
