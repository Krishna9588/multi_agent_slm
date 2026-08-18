import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from agents.web_scraper import web_scraper

def test_web_scraper_invalid_url():
    """Verify web scraper handles invalid URLs gracefully."""
    result = web_scraper("invalid_url_format")
    assert "error" in result or "text" in result

if __name__ == "__main__":
    url = "https://en.wikipedia.org/wiki/Python_(programming_language)"
    result = web_scraper(url, strategy="requests", output_format="markdown")
    print(result.get("text", "")[:500])
