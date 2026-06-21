# Wikipedia Translation Assistant

A semi-automatic Wikipedia translation helper. This tool fetches article wikitext from Wikipedia, shows the source, generates a placeholder translation draft, runs quality checks, and exports copy-ready wikitext for manual review.

**This is a translation assistant, not an auto-publishing bot.** Do not publish machine-generated or unreviewed AI translations to Wikipedia.

## What it does

### Phase 1 (MVP)

- Fetch the latest wikitext source of a Wikipedia article via the MediaWiki API
- Preview the original wikitext
- Generate a draft translation (placeholder in v1)
- Export copy-ready wikitext for human editing

### Phase 2 (Quality checks)

- **Template Check** — compare templates in source vs. translation draft
- **Reference Check** — compare `<ref>` tags, named refs, and bibliographic metadata
- **Korean Style Check** — flag formal/polite Korean (~입니다/~합니다) unsuitable for Korean Wikipedia's encyclopedic style (~이다/~한다)

These checks are **assistive only**. They cannot replace human proofreading. Do not publish AI translations without thorough manual review. All new factual content on Wikipedia must cite reliable sources.

## Requirements

- Python 3.10+
- macOS or Windows (also suitable for [Streamlit Community Cloud](https://streamlit.io/cloud) deployment)

## Installation

```bash
git clone <your-repo-url>
cd wiki-translation-assistant

python -m venv .venv

# macOS / Linux
source .venv/bin/activate

# Windows
.venv\Scripts\activate

pip install -r requirements.txt
```

## Run locally

```bash
streamlit run app.py
```

Open the URL shown in the terminal (usually `http://localhost:8501`).

### UI (editorial review style)

The interface uses a light, Wikipedia-inspired editorial layout:

- White / light-gray workspace with Wikipedia blue accents
- Sidebar project controls (languages, title, fetch, generate draft)
- Main tabs for source review, draft review, compliance checks, export, and about
- Status labels: Passed, Warning, Needs review, Info

### Usage

1. In the **sidebar**, set **Source language** (e.g. `en`), **Target language** (e.g. `ko`), and **Article title** (e.g. `Alan Turing`).
2. Click **Fetch article** in the sidebar to load wikitext.
3. Click **Generate draft** to create a placeholder translation draft.
4. **Article Source** — preview fetched wikitext.
5. **Translation Draft** — preview the draft.
6. **Template Check** — verify Infobox, citation templates, and other templates are preserved.
7. **Reference Check** — verify refs, named refs, URLs, DOIs, ISBNs, and other metadata.
8. **Korean Style Check** — review suggestions for encyclopedic Korean style (when targeting `ko`).
9. **Export** — copy or download the draft wikitext after manual review.
10. **About** — workflow and policy reminders.

## Quality check details

### Template Check

Compares every `{{template}}` in source and translation wikitext using `mwparserfromhell`. Reports:

- Templates present in source but missing in translation (and vice versa)
- Whether an Infobox is preserved
- Citation template counts (`cite web`, `cite news`, `cite journal`, `cite book`, etc.)
- Warnings for templates that may need target-language localization (`authority control`, `DEFAULTSORT`, `short description`, `navbox`, …)

The tool **does not delete or modify templates** — it only shows warnings and suggestions.

### Reference Check

Counts and compares:

- `<ref>` tags, named refs, and self-closing refs
- Citation templates
- Bibliographic fields: URL, DOI, ISBN, pages, access-date, publisher, title

Flags issues such as unclosed refs, missing named refs, fewer refs in translation, or possible unsourced new content. Reminds you that **unsourced AI content violates Wikipedia policy** and may lead to deletion or sanctions.

### Korean Style Check

Scans the translation draft for formal endings like `입니다`, `합니다`, `했습니다`, and suggests encyclopedic alternatives (`이다`, `한다`, `하였다`, …). Suggestions require human judgment — the tool never auto-replaces text.

## Important disclaimer

- **Do not automatically publish AI or machine translations to Wikipedia.**
- All output must be reviewed and edited by a human translator before any submission.
- **All new factual statements must have reliable references.**
- This tool does not connect to Wikipedia edit APIs and cannot publish on your behalf.

## Project structure

| File | Purpose |
|------|---------|
| `app.py` | Streamlit UI |
| `wiki_api.py` | MediaWiki API client (fetch wikitext) |
| `translator.py` | Translation logic (MVP placeholder) |
| `validator.py` | Input validation + template/reference/Korean style checkers |
| `requirements.txt` | Python dependencies |

## Planned future features

- Link check (interwiki / red links)
- Publishing checklist before submission

## License

Add your license here.
