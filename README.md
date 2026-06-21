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

### Phase 4 (Publishing compliance & final review)

- **Talk Page Templates** — generate translated-page and educational-assignment template suggestions
- **Translation Attribution** — generate recommended edit summaries and history-check reminders
- **Educational Assignment Helper** — suggest course assignment templates for talk pages
- **Page Move Checklist** — remind editors to move drafts to mainspace instead of copy-pasting when appropriate
- **Edit Filter Risk Report** — flag policy risks and suggest compliant fixes
- **Final Publishing Checklist** — combine all prior checks into a final human review list

These checks are **assistive only**. They cannot replace human proofreading. Do not publish AI translations without thorough manual review. All new factual content on Wikipedia must cite reliable sources. Image copyright must always be confirmed manually. Do not try to bypass edit filters; fix the underlying policy or content issue instead.

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
- Main tabs for source review, draft review, compliance checks, publishing checks, export, and about
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
12. **Publishing Checklist** — review mainspace move, title, redirects, categories, references, and post-publication monitoring.
13. **Talk Page Templates** — prepare talk page templates for translated pages and educational assignments.
14. **Attribution** — prepare a translation-source edit summary.
15. **Edit Filter Risk** — review possible moderation risks and safe compliance fixes.
16. **Final Review** — combine all checks into a final publication-readiness list.
17. **Export** — copy or download the draft wikitext after manual review.
18. **About** — workflow and policy reminders.

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

### Talk Page Templates

Generates talk page template suggestions for translated articles and educational assignments:

- Korean: `ko:틀:번역된_문서`, `ko:틀:과제 문서`
- Chinese: `zh:Template:Translated page`, `zh:Template:Educational assignment`
- English: `Template:Translated page`, `{{Educational assignment}}`

These templates should be placed on the **talk page**, not in the article body.

### Translation Attribution

Generates a recommended edit summary such as:

- English: `Translated from English Wikipedia article "Article Title"; see its history for attribution.`
- Korean: `한국어 번역: 영어 위키백과 "Article Title" 문서에서 번역함.`
- Chinese: `翻译自英文维基百科条目“Article Title”，版权归其贡献者所有，见原文历史记录。`

Editors must still check the original article history and identify the translated revision.

### Educational Assignment Helper

Suggests a talk page assignment template when the draft is part of a class or course project. Educational assignment templates should not be placed in the article page body.

### Page Move Checklist

Reviews publishing reminders:

- Whether the title appears to be in User / Draft namespace
- Whether the target title may already exist
- Whether redirects may be needed
- Whether references section and categories are present
- Whether categories should be blue-linked
- Whether interlanguage links / Wikidata sitelinks may need follow-up
- Whether article history and talk page should be monitored after publishing

The tool does **not** move pages automatically.

### Edit Filter Risk Report

Flags risks such as large unsourced additions, too many external links, machine-translation traces, promotional tone, suspicious URLs, disrupted templates, too few references, missing attribution, missing proofreading confirmation, or Korean polite style in a Korean article.

It only suggests compliant fixes:

- Add or restore reliable citations
- Remove unsourced content
- Review in a sandbox
- Proofread manually
- Check links and templates
- Split large edits when appropriate

It does **not** provide ways to bypass edit filters.

### Final Publishing Checklist

Combines all checks into a final publication-readiness list covering translation completion, references, unsourced AI content, templates, infobox, Korean style, blue/red links, image copyright, categories, references section, talk page templates, attribution, educational assignment, page move review, edit filter risk, and human proofreading.

## Important disclaimer

- **Do not automatically publish AI or machine translations to Wikipedia.**
- All output must be reviewed and edited by a human translator before any submission.
- **All new factual statements must have reliable references.**
- **Image copyright and fair-use status must be checked manually.**
- **Do not attempt to bypass edit filters.**
- **Human proofreading is required before publication.**
- After publishing, monitor article history and the talk page for feedback.
- This tool does not connect to Wikipedia edit APIs and cannot publish on your behalf.

## Project structure

| File | Purpose |
|------|---------|
| `app.py` | Streamlit UI |
| `wiki_api.py` | MediaWiki API client (fetch wikitext, page status, language links) |
| `translator.py` | Translation logic (MVP placeholder) |
| `validator.py` | Input validation + template/reference/link/media/category/structure/publishing/Korean style checkers |
| `requirements.txt` | Python dependencies |

## Planned future features

- Link localization improvements
- More detailed target-wiki policy guidance

## License

Add your license here.
