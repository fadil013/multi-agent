"""Web search tool - wraps Tavily for use by agents (primarily Research Agent).

Owner: Ahmad (tools)
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv
from tavily import TavilyClient

load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env")


@dataclass
class SearchResult:
    title: str
    url: str
    content: str


def web_search(query: str, max_results: int = 5) -> list[SearchResult]:
    """Search the web and return structured results with sources.

    Raises RuntimeError if the search API call fails, so callers
    (agents) can decide how to handle a failed search rather than
    silently getting an empty list that looks like "no results found".
    """
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        raise ValueError("TAVILY_API_KEY not found in .env")

    client = TavilyClient(api_key=api_key)

    try:
        response = client.search(query, max_results=max_results)
    except Exception as e:
        raise RuntimeError(f"Web search failed for query '{query}': {e}") from e

    return [
        SearchResult(
            title=r.get("title", ""),
            url=r.get("url", ""),
            content=r.get("content", ""),
        )
        for r in response.get("results", [])
    ]


if __name__ == "__main__":
    results = web_search("electric vehicle market growth 2026")
    for r in results:
        print(f"{r.title}\n{r.url}\n{r.content[:150]}\n")