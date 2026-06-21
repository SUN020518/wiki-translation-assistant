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

### Phase 3 (Link & wiki structure checks)

- **Link Check** — extract internal links and estimate blue-link / red-link risk on the target-language Wikipedia
- **Temporary link template suggestions** — suggest interlanguage temporary link templates such as `ko:틀:임시링크`, `zh:Template:Internal link helper`, or `Template:Interlanguage link`
- **Disambiguation warning** — flag links that may point to disambiguation pages
- **Image & Category Check** — list source image files, warn about image copyright / fair use, and compare categories
- **References Section Check** — verify target-language references section headings such as `References`, `각주`, `参考资料`, or `參考資料`

These checks are **assistive only**. They cannot replace human proofreading. Do not publish AI translations without thorough manual review. All new factual content on Wikipedia must cite reliable sources. Image copyright must always be confirmed manually.

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
- Main tabs for source review, draft review, compliance checks, structure checks, export, and about
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
9. **Link Check** — review blue-link status, red-link risk, and temporary link template suggestions.
10. **Image & Category Check** — review image files, copyright cautions, and target-wiki categories.
11. **Structure Check** — verify references section status and disambiguation warnings.
12. **Export** — copy or download the draft wikitext after manual review.
13. **About** — workflow and policy reminders.

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

### Link Check

Extracts regular internal article links such as `[[Alan Turing]]` or `[[University of Cambridge|Cambridge]]`, checks target-language Wikipedia page availability when possible, and reports:

- Blue-link candidates
- Red-link risk
- Unknown links that require manual verification
- Suggested temporary interlanguage link templates

The tool does **not** automatically rewrite article links.

### Disambiguation Warning

Uses MediaWiki category data to flag pages that may be disambiguation pages. This is a warning only — editors must manually confirm the correct target page.

### Image & Category Check

Lists `File:` / `Image:` links and compares source vs. draft categories. It reminds editors that:

- Wikimedia Commons free-license images are usually safer, but still require review
- Fair use images may not be allowed on Korean Wikipedia
- Chinese Wikipedia has its own non-free content rules
- Images copied from the internet are not safe unless licensing is clearly compatible
- Categories should be target-wiki categories and should ideally be blue-linked

The tool does not download, upload, or license-check image files automatically.

### References Section Check

Checks whether the draft contains a target-language references section heading:

- English: `References`
- Korean: `각주`
- Chinese: `参考资料` or `參考資料`

If missing, the tool shows a warning before export.

## Important disclaimer

- **Do not automatically publish AI or machine translations to Wikipedia.**
- All output must be reviewed and edited by a human translator before any submission.
- **All new factual statements must have reliable references.**
- **Image copyright and fair-use status must be checked manually.**
- This tool does not connect to Wikipedia edit APIs and cannot publish on your behalf.

## Project structure

| File | Purpose |
|------|---------|
| `app.py` | Streamlit UI |
| `wiki_api.py` | MediaWiki API client (fetch wikitext, page status, language links) |
| `translator.py` | Translation logic (MVP placeholder) |
| `validator.py` | Input validation + template/reference/link/media/category/structure/Korean style checkers |
| `requirements.txt` | Python dependencies |

## Planned future features

- Publishing checklist before submission
- Link localization improvements
- More detailed target-wiki policy guidance

## License

Add your license here.
