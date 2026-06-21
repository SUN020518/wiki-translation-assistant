"""Wikipedia Translation Assistant — Streamlit MVP."""

from __future__ import annotations

import streamlit as st

from translator import PLACEHOLDER_MARKER, translate_text
from validator import validate_lang_code, validate_title
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


def main() -> None:
    _init_session_state()

    st.title("Wikipedia Translation Assistant")
    st.markdown(
        "Fetch Wikipedia source wikitext, generate a draft translation, "
        "and export for manual review."
    )
    st.info(DISCLAIMER)

    _render_sidebar()

    validated = _validate_inputs()
    if validated is None:
        st.stop()

    source_lang, target_lang, title = validated

    tab_fetch, tab_translate, tab_export = st.tabs(
        ["Fetch Article", "Translate Draft", "Export"]
    )

    with tab_fetch:
        _tab_fetch(source_lang, target_lang, title)

    with tab_translate:
        _tab_translate(source_lang, target_lang, title)

    with tab_export:
        _tab_export()


if __name__ == "__main__":
    main()
