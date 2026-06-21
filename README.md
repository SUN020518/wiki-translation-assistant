# Wikipedia Translation Assistant

A semi-automatic Wikipedia translation helper. This MVP fetches article wikitext from Wikipedia, shows the source, generates a placeholder translation draft, and exports copy-ready wikitext for manual review.

**This is a translation assistant, not an auto-publishing bot.** Do not publish machine-generated or unreviewed AI translations to Wikipedia.

## What it does (MVP)

- Fetch the latest wikitext source of a Wikipedia article via the MediaWiki API
- Preview the original wikitext
- Generate a draft translation (placeholder in v1)
- Export copy-ready wikitext for human editing

## Requirements

- Python 3.10+
- macOS or Windows (also suitable for [Streamlit Community Cloud](https://streamlit.io/cloud) deployment later)

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

### Usage

1. Set **Source language** (e.g. `en`), **Target language** (e.g. `ko`, `zh`, `ja`), and **Article title** (e.g. `Alan Turing`) in the sidebar.
2. **Fetch Article** — load wikitext from the source wiki. If the article does not exist, a clear error is shown.
3. **Translate Draft** — generate a placeholder draft (marked with `[TRANSLATION PLACEHOLDER]`).
4. **Export** — copy or download the draft wikitext for manual review and editing.

## Important disclaimer

- **Do not automatically publish AI or machine translations to Wikipedia.**
- All output must be reviewed and edited by a human translator before any submission.
- This tool does not connect to Wikipedia edit APIs and cannot publish on your behalf.

## Project structure

| File | Purpose |
|------|---------|
| `app.py` | Streamlit UI |
| `wiki_api.py` | MediaWiki API client (fetch wikitext) |
| `translator.py` | Translation logic (MVP placeholder) |
| `validator.py` | Input validation |
| `requirements.txt` | Python dependencies |

## Planned future features

- References check
- Template check
- Link check (interwiki / red links)
- Publishing checklist before submission

## License

Add your license here.
