"""Fetch Wikipedia article wikitext via the MediaWiki API."""

from __future__ import annotations

import requests

USER_AGENT = "WikiTranslationAssistant/0.1 (https://github.com/example/wiki-translation-assistant; local dev tool)"
REQUEST_TIMEOUT = 30


class WikiArticleNotFoundError(Exception):
    """Raised when the requested article does not exist on the source wiki."""


class WikiAPIError(Exception):
    """Raised when the MediaWiki API returns an unexpected error."""


def _api_url(lang: str) -> str:
    return f"https://{lang.strip().lower()}.wikipedia.org/w/api.php"


def fetch_wikitext(lang: str, title: str) -> str:
    """
    Fetch the latest revision wikitext for a Wikipedia article.

    Args:
        lang: Wikipedia language code (e.g. "en").
        title: Article title (e.g. "Alan Turing").

    Returns:
        Raw wikitext source of the article.

    Raises:
        WikiArticleNotFoundError: If the page does not exist.
        WikiAPIError: If the API request fails or returns invalid data.
    """
    params = {
        "action": "query",
        "format": "json",
        "titles": title,
        "prop": "revisions",
        "rvprop": "content",
        "rvslots": "main",
        "redirects": 1,
    }
    headers = {"User-Agent": USER_AGENT}

    try:
        response = requests.get(
            _api_url(lang),
            params=params,
            headers=headers,
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        raise WikiAPIError(f"Failed to reach Wikipedia API: {exc}") from exc

    try:
        data = response.json()
    except ValueError as exc:
        raise WikiAPIError("Wikipedia API returned invalid JSON.") from exc

    if "error" in data:
        code = data["error"].get("code", "unknown")
        info = data["error"].get("info", "Unknown API error.")
        raise WikiAPIError(f"Wikipedia API error ({code}): {info}")

    pages = data.get("query", {}).get("pages", {})
    if not pages:
        raise WikiAPIError("Wikipedia API returned no page data.")

    page = next(iter(pages.values()))
    page_id = page.get("pageid")
    if page_id is None or page_id == -1:
        raise WikiArticleNotFoundError(
            f'Article "{title}" was not found on {lang}.wikipedia.org.'
        )

    revisions = page.get("revisions", [])
    if not revisions:
        raise WikiAPIError("Article exists but no revision content was returned.")

    slots = revisions[0].get("slots", {})
    main_slot = slots.get("main", revisions[0])
    content = main_slot.get("*") or main_slot.get("content", "")

    if not content:
        raise WikiAPIError("Article revision content is empty.")

    return content
