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


import urllib.request
import urllib.parse
import json

# ── Backend implementations ────────────────────────────────────────────────────

def _search_duckduckgo(query: str, max_results: int = 4) -> list[dict]:
    # 1. Try modern ddgs / duckduckgo_search library
    try:
        try:
            from ddgs import DDGS
        except ImportError:
            from duckduckgo_search import DDGS
        with DDGS() as ddgs_client:
            raw = list(ddgs_client.text(query, max_results=max_results))
            if raw:
                return [
                    {
                        "title":   r.get("title", ""),
                        "url":     r.get("href", ""),
                        "snippet": r.get("body", ""),
                        "source":  "duckduckgo",
                    }
                    for r in raw
                ]
    except Exception:
        pass

    # 2. Zero-dependency HTTP fallback via DuckDuckGo HTML
    try:
        url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}"
        req = urllib.request.Request(
            url, 
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            html_text = resp.read().decode('utf-8', errors='ignore')
            
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html_text, "html.parser")
            results = []
            for res in soup.find_all("div", class_="result")[:max_results]:
                a_tag = res.find("a", class_="result__url") or res.find("a", class_="result__snippet")
                title_tag = res.find("a", class_="result__title")
                snippet_tag = res.find("a", class_="result__snippet")
                if title_tag:
                    href = title_tag.get("href", "")
                    if "uddg=" in href:
                        # Extract actual target URL from DuckDuckGo redirect
                        m = re.search(r"uddg=([^&]+)", href)
                        if m:
                            href = urllib.parse.unquote(m.group(1))
                    results.append({
                        "title": title_tag.get_text(strip=True),
                        "url": href,
                        "snippet": snippet_tag.get_text(strip=True) if snippet_tag else "",
                        "source": "duckduckgo_html"
                    })
            if results:
                return results
        except Exception:
            pass
    except Exception:
        pass

    return []


def _search_wikipedia(query: str, max_results: int = 4) -> list[dict]:
    # 1. Try wikipedia python package
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
        if results:
            return results
    except Exception:
        pass

    # 2. Zero-dependency Wikipedia OpenSearch REST API fallback
    try:
        api_url = f"https://en.wikipedia.org/w/api.php?action=opensearch&search={urllib.parse.quote(query)}&limit={max_results}&format=json"
        req = urllib.request.Request(api_url, headers={"User-Agent": "AutonomousMultiAgent/1.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            titles, snippets, urls = data[1], data[2], data[3]
            results = []
            for t, s, u in zip(titles, snippets, urls):
                results.append({
                    "title": t,
                    "url": u,
                    "snippet": s or f"Wikipedia article on {t}",
                    "source": "wikipedia_api"
                })
            return results
    except Exception:
        pass

    return []


def _search_arxiv(query: str, max_results: int = 4) -> list[dict]:
    # 1. Try arxiv package
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
        if results:
            return results
    except Exception:
        pass

    # 2. Zero-dependency arXiv Atom Feed REST API fallback
    try:
        api_url = f"http://export.arxiv.org/api/query?search_query=all:{urllib.parse.quote(query)}&start=0&max_results={max_results}"
        req = urllib.request.Request(api_url, headers={"User-Agent": "AutonomousMultiAgent/1.0"})
        with urllib.request.urlopen(req, timeout=6) as resp:
            xml_text = resp.read().decode('utf-8')
            
        import xml.etree.ElementTree as ET
        root = ET.fromstring(xml_text)
        ns = {'atom': 'http://www.w3.org/2005/Atom'}
        results = []
        for entry in root.findall('atom:entry', ns)[:max_results]:
            title = entry.find('atom:title', ns)
            summary = entry.find('atom:summary', ns)
            link = entry.find('atom:id', ns)
            if title is not None and link is not None:
                results.append({
                    "title": title.text.strip().replace('\n', ' '),
                    "url": link.text.strip(),
                    "snippet": summary.text.strip().replace('\n', ' ')[:300] if summary is not None else "",
                    "source": "arxiv_api"
                })
        return results
    except Exception:
        pass

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
