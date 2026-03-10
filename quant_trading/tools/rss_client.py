from __future__ import annotations

import re
from typing import Any


COMMON_SUFFIXES = {"limited", "ltd", "ltd.", "industries", "industry", "inc", "corp", "company", "co", "plc"}


def _query_terms(query: str) -> tuple[set[str], str]:
    words = [token for token in re.findall(r"[a-z0-9]+", query.lower()) if len(token) >= 3]
    filtered = {token for token in words if token not in COMMON_SUFFIXES}
    acronym = "".join(token[0] for token in words if token not in COMMON_SUFFIXES and token.isalpha())
    return filtered or set(words), acronym


class RSSClient:
    def __init__(self, feeds: list[str] | None = None) -> None:
        self.feeds = feeds or []

    def search(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        try:
            import feedparser  # type: ignore
        except ImportError:
            return []
        query_terms, acronym = _query_terms(query)
        results: list[dict[str, Any]] = []
        for feed_url in self.feeds:
            parsed = feedparser.parse(feed_url)
            for entry in parsed.entries:
                title = getattr(entry, "title", "")
                normalized_title = title.lower()
                title_terms = set(re.findall(r"[a-z0-9]+", normalized_title))
                if query.lower() in normalized_title or query_terms.intersection(title_terms) or (acronym and acronym.lower() in normalized_title):
                    results.append(
                        {
                            "title": title,
                            "link": getattr(entry, "link", ""),
                            "published": getattr(entry, "published", ""),
                        }
                    )
                    if len(results) >= limit:
                        return results
        return results
