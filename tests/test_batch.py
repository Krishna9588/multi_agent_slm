import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from agents.batch_scraper_agent import batch_scraper_agent

def test_batch_scraper_empty():
    """Verify batch scraper handles empty URL lists."""
    result = batch_scraper_agent([])
    assert "error" in result or result.get("total_urls") == 0

def test_batch_scraper_invalid():
    """Verify batch scraper handles non-existent URLs gracefully without crashing."""
    result = batch_scraper_agent(["https://invalid.example.test/nonexistent"])
    assert result.get("total_urls") == 1
    assert "https://invalid.example.test/nonexistent" in result.get("results", {})

if __name__ == "__main__":
    urls = ["https://en.wikipedia.org/wiki/Python_(programming_language)", "https://en.wikipedia.org/wiki/Artificial_intelligence"]
    print(f"Testing batch scraper on {len(urls)} URLs...")
    result = batch_scraper_agent(urls, strategy="requests", output_format="markdown", max_words_per_page=300)
    print("Batch Scrape Complete. Total URLs:", result.get("total_urls"))


