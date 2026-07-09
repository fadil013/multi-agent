"""Web search tool - used by the Research Agent.

Owner: Ahmad
"""
from __future__ import annotations


def web_search(query: str, max_results: int = 5) -> list[dict]:
    """Search the web and return results as [{title, url, snippet}]."""
    # TODO: call a search API (Tavily / SerpAPI) and normalise the results
    raise NotImplementedError("Ahmad: implement web search")
