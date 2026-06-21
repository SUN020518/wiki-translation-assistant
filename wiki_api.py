"""Fetch Wikipedia article wikitext via the MediaWiki API."""

from __future__ import annotations

import requests

USER_AGENT = "WikiTranslationAssistant/0.1 (https://github.com/example/wiki-translation-assistant; local dev tool)"
REQUEST_TIMEOUT = 30
PAGE_STATUS_BATCH_SIZE = 50


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


def _request_api(lang: str, params: dict[str, str | int]) -> dict:
    """Call a MediaWiki API endpoint and return parsed JSON."""
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

    return data


def _chunks(values: list[str], size: int) -> list[list[str]]:
    """Split values into API-friendly batches."""
    return [values[index : index + size] for index in range(0, len(values), size)]


def get_language_link_candidates(
    source_lang: str,
    titles: list[str],
    target_lang: str,
) -> dict[str, str]:
    """
    Find target-language page titles using source wiki langlinks.

    Returns a mapping from source title to target-language title where available.
    """
    if not titles:
        return {}

    candidates: dict[str, str] = {}
    unique_titles = list(dict.fromkeys(title.strip() for title in titles if title.strip()))

    for batch in _chunks(unique_titles, PAGE_STATUS_BATCH_SIZE):
        params = {
            "action": "query",
            "format": "json",
            "titles": "|".join(batch),
            "prop": "langlinks",
            "lllang": target_lang.strip().lower(),
            "lllimit": "max",
            "redirects": 1,
        }
        data = _request_api(source_lang, params)
        normalized = {
            item.get("from"): item.get("to")
            for item in data.get("query", {}).get("normalized", [])
            if item.get("from") and item.get("to")
        }
        redirects = {
            item.get("from"): item.get("to")
            for item in data.get("query", {}).get("redirects", [])
            if item.get("from") and item.get("to")
        }
        pages = data.get("query", {}).get("pages", {})
        for page in pages.values():
            source_title = page.get("title", "")
            requested_titles = [
                requested
                for requested in batch
                if requested == source_title
                or normalized.get(requested) == source_title
                or redirects.get(requested) == source_title
                or redirects.get(normalized.get(requested, "")) == source_title
            ] or [source_title]
            langlinks = page.get("langlinks", [])
            if langlinks:
                candidate = langlinks[0].get("*", "")
                for requested in requested_titles:
                    candidates[requested] = candidate

    return candidates


def check_pages_status(lang: str, titles: list[str]) -> dict[str, dict[str, object]]:
    """
    Check whether pages exist and whether they may be disambiguation pages.

    Returns a mapping keyed by requested title.
    """
    if not titles:
        return {}

    unique_titles = list(dict.fromkeys(title.strip() for title in titles if title.strip()))
    results: dict[str, dict[str, object]] = {
        title: {
            "exists": False,
            "normalized_title": title,
            "possible_disambiguation": False,
            "categories": [],
        }
        for title in unique_titles
    }

    for batch in _chunks(unique_titles, PAGE_STATUS_BATCH_SIZE):
        params = {
            "action": "query",
            "format": "json",
            "titles": "|".join(batch),
            "prop": "categories",
            "cllimit": "max",
            "redirects": 1,
        }
        data = _request_api(lang, params)

        normalized = {
            item.get("from"): item.get("to")
            for item in data.get("query", {}).get("normalized", [])
            if item.get("from") and item.get("to")
        }
        redirects = {
            item.get("from"): item.get("to")
            for item in data.get("query", {}).get("redirects", [])
            if item.get("from") and item.get("to")
        }

        pages = data.get("query", {}).get("pages", {})
        for page in pages.values():
            normalized_title = page.get("title", "")
            requested_titles = [
                requested
                for requested in batch
                if requested == normalized_title
                or normalized.get(requested) == normalized_title
                or redirects.get(requested) == normalized_title
                or redirects.get(normalized.get(requested, "")) == normalized_title
            ] or [normalized_title]

            categories = [
                category.get("title", "")
                for category in page.get("categories", [])
                if category.get("title")
            ]
            category_text = " ".join(categories).lower()
            possible_disambiguation = any(
                keyword in category_text
                for keyword in (
                    "disambiguation",
                    "동음이의",
                    "동명이인",
                    "消歧义",
                    "消歧義",
                )
            )

            status = {
                "exists": "missing" not in page,
                "normalized_title": normalized_title,
                "possible_disambiguation": possible_disambiguation,
                "categories": categories,
            }
            for requested in requested_titles:
                results[requested] = status

    return results
