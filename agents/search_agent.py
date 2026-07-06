"""
Agent: search_agent
-------------------
Pillar 1: Internet & Discovery Layer.

Provides a smart search gateway with automatic backend routing and fallback:
  1. DuckDuckGo (DDGS) — general web queries, no API key needed.
  2. Wikipedia      — factual / encyclopedic queries (who, what, define).
  3. ArXiv          — technical / research queries (papers, algorithms, models).

Backend is selected automatically based on query keyword signals.
If the primary backend fails or returns empty, the next one is tried.

Primary function: search_agent(query, backend="auto")
"""

import re
from typing import Optional

# ── Agent metadata ─────────────────────────────────────────────────────────────

DESCRIPTION = (
    "Search the internet for real-time information or to find URLs related to a query. "
    "Returns the top results with title, URL, and snippet. "
    "Automatically routes to DuckDuckGo (general), Wikipedia (factual), or ArXiv (research). "
    "Use this when you need live data, don't know the exact URL, or need factual/research references."
)

PARAMETERS = {
    "query": {
        "type":        "string",
        "required":    True,
        "description": "The search query string.",
    },
    "backend": {
        "type":        "string",
        "required":    False,
        "description": (
            "Search backend to use. "
            "'auto' (default) selects the best backend based on query type. "
            "Options: auto | duckduckgo | wikipedia | arxiv"
        ),
    },
}

# ── Query routing signals ──────────────────────────────────────────────────────

_WIKIPEDIA_SIGNALS = [
    "who is", "who was", "what is", "what are", "define", "history of",
    "biography", "founded", "born", "meaning of", "explain",
]

_ARXIV_SIGNALS = [
    "paper", "research", "arxiv", "algorithm", "model", "neural", "transformer",
    "deep learning", "machine learning", "llm", "diffusion", "attention",
    "benchmark", "dataset", "architecture", "preprint",
]


def _detect_backend(query: str) -> str:
    """Auto-detect the best backend based on query content."""
    q_lower = query.lower()
    for signal in _ARXIV_SIGNALS:
        if signal in q_lower:
            return "arxiv"
    for signal in _WIKIPEDIA_SIGNALS:
        if signal in q_lower:
            return "wikipedia"
    return "duckduckgo"


# ── Backend implementations ────────────────────────────────────────────────────

def _search_duckduckgo(query: str, max_results: int = 4) -> list[dict]:
    try:
        # Try new package name 'ddgs' first, fall back to legacy 'duckduckgo_search'
        try:
            from ddgs import DDGS
        except ImportError:
            from duckduckgo_search import DDGS
        with DDGS() as ddgs_client:
            raw = list(ddgs_client.text(query, max_results=max_results))
            return [
                {
                    "title":   r.get("title", ""),
                    "url":     r.get("href", ""),
                    "snippet": r.get("body", ""),
                    "source":  "duckduckgo",
                }
                for r in raw
            ]
    except ImportError:
        return []
    except Exception:
        return []


def _search_wikipedia(query: str, max_results: int = 4) -> list[dict]:
    try:
        import wikipedia
        search_titles = wikipedia.search(query, results=max_results)
        results = []
        for title in search_titles[:max_results]:
            try:
                page = wikipedia.page(title, auto_suggest=False)
                results.append({
                    "title":   page.title,
                    "url":     page.url,
                    "snippet": page.summary[:300],
                    "source":  "wikipedia",
                })
            except Exception:
                continue
        return results
    except ImportError:
        return []
    except Exception:
        return []


def _search_arxiv(query: str, max_results: int = 4) -> list[dict]:
    try:
        import arxiv
        client = arxiv.Client()
        search = arxiv.Search(query=query, max_results=max_results)
        results = []
        for paper in client.results(search):
            results.append({
                "title":   paper.title,
                "url":     paper.entry_id,
                "snippet": paper.summary[:300],
                "source":  "arxiv",
            })
        return results
    except ImportError:
        return []
    except Exception:
        return []


# ── Primary function ───────────────────────────────────────────────────────────

def search_agent(query: str, backend: str = "auto") -> dict:
    """
    Search the internet and return structured results.

    Args:
        query:   The search string.
        backend: 'auto' | 'duckduckgo' | 'wikipedia' | 'arxiv'

    Returns:
        dict with 'query', 'backend_used', and 'results' list.
    """
    if not query or not query.strip():
        return {"error": "Empty query provided."}

    # Determine backend order
    if backend == "auto":
        primary = _detect_backend(query)
    else:
        primary = backend

    # Define fallback chain
    _all_backends = ["duckduckgo", "wikipedia", "arxiv"]
    chain = [primary] + [b for b in _all_backends if b != primary]

    _fn_map = {
        "duckduckgo": _search_duckduckgo,
        "wikipedia":  _search_wikipedia,
        "arxiv":      _search_arxiv,
    }

    for backend_name in chain:
        fn = _fn_map.get(backend_name)
        if fn is None:
            continue
        results = fn(query)
        if results:
            return {
                "query":        query,
                "backend_used": backend_name,
                "results":      results,
                "total":        len(results),
            }

    return {
        "error":   f"All search backends returned no results for: '{query}'",
        "query":   query,
        "results": [],
        "total":   0,
    }
