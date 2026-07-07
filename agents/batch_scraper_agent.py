"""
Agent: batch_scraper_agent
----------------------------
Takes a list of URLs and scrapes them concurrently using web_scraper.
Useful for deep-link scraping, paginated extraction, or aggregating data from multiple sites.

Primary function: batch_scraper_agent(urls, strategy="auto", output_format="markdown", max_words_per_page=1500)
"""

import concurrent.futures
import json
from typing import List
from agents.web_scraper import web_scraper

# ── Agent metadata ─────────────────────────────────────────────────────────────

DESCRIPTION = (
    "Scrapes multiple URLs concurrently and returns their extracted content as a JSON map. "
    "CRITICAL: Use this tool whenever you need to click into or visit a list of links (e.g., job postings, articles) "
    "to extract detailed data from each sub-page simultaneously."
)

PARAMETERS = {
    "urls": {
        "type":        "array",
        "items":       {"type": "string"},
        "required":    True,
        "description": "List of full URLs to scrape.",
    },
    "strategy": {
        "type":        "string",
        "required":    False,
        "description": "Scraping strategy (auto, urllib, requests, parsel, playwright). Default is 'auto'.",
    },
    "output_format": {
        "type":        "string",
        "required":    False,
        "description": "Output format: 'text' or 'markdown'. Default is 'markdown' to preserve structure.",
    },
    "max_words_per_page": {
        "type":        "integer",
        "required":    False,
        "description": "Max words to extract per page to avoid context flooding. Default is 1500.",
    }
}

# ── Primary function ───────────────────────────────────────────────────────────

def _scrape_single(url: str, strategy: str, output_format: str, max_words: int) -> dict:
    try:
        # Call the existing web_scraper for a single URL
        result = web_scraper(url, strategy=strategy, output_format=output_format, max_words=max_words)
        return {"url": url, "result": result}
    except Exception as e:
        return {"url": url, "error": str(e)}

def batch_scraper_agent(
    urls: List[str], 
    strategy: str = "auto", 
    output_format: str = "markdown", 
    max_words_per_page: int = 1500,
    **kwargs
) -> dict:
    """
    Fetch a list of URLs concurrently and return their structured contents.
    """
    if not urls or not isinstance(urls, list):
        return {"error": "'urls' must be a non-empty list of strings."}

    results = {}
    
    # Use a ThreadPoolExecutor to scrape in parallel
    # Max workers set to 5 to avoid overwhelming local network or getting instantly IP banned
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [
            executor.submit(_scrape_single, url, strategy, output_format, max_words_per_page)
            for url in urls
        ]
        
        for future in concurrent.futures.as_completed(futures):
            data = future.result()
            url = data["url"]
            if "error" in data:
                results[url] = {"error": data["error"]}
            else:
                # We only need the title and text to save LLM tokens
                scrape_res = data["result"]
                results[url] = {
                    "title": scrape_res.get("title", ""),
                    "text": scrape_res.get("text", "")
                }

    return {
        "status": "success",
        "total_urls": len(urls),
        "results": results
    }
