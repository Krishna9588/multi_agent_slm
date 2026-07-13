from langchain_core.tools import tool

import os
import json
from langchain_core.tools import tool
from agents.web_scraper import web_scraper
from agents.link_extractor import link_extractor

@tool
def robust_web_scraper(url: str) -> str:
    """
    Scrapes a webpage using a robust local strategy cascade (urllib -> requests -> playwright).
    Returns the clean, extracted text from the page.
    """
    try:
        # Use our pre-built web_scraper from the legacy agents folder
        result = web_scraper(url)
        return result.get("text", f"Failed to scrape. Error: {result.get('error')}")
    except Exception as e:
        return f"Error scraping {url}: {str(e)}"

@tool
def get_internal_links(url: str) -> list[str]:
    """
    Extracts all internal hyperlinks from a given URL so the agent can discover sub-pages (e.g., About, Contact).
    """
    try:
        links_data = link_extractor(url)
        return links_data.get("internal_links", [])
    except Exception as e:
        return [f"Error extracting links: {str(e)}"]

@tool
def apify_linkedin_scraper(linkedin_url: str) -> str:
    """
    Uses the Apify API to scrape a LinkedIn profile (company or individual).
    Requires the APIFY_API_TOKEN environment variable.
    """
    token = os.environ.get("APIFY_API_TOKEN")
    if not token:
        return "Error: APIFY_API_TOKEN environment variable is not set. Cannot scrape LinkedIn."
        
    try:
        from apify_client import ApifyClient
        client = ApifyClient(token)
        
        # We use a popular reliable linkedin scraper actor, e.g. "curious_coder/linkedin-profile-scraper" 
        # or the official apify linkedin actors. Let's use 'quacker/linkedin-profile-scraper' or similar.
        # For safety, since actors change, we will try standard 'curious_coder/linkedin-profile-scraper'
        run = client.actor("curious_coder/linkedin-profile-scraper").call(run_input={
            "urls": [linkedin_url]
        })
        
        items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
        if items:
            return json.dumps(items[0], indent=2)
        return f"Apify ran successfully but no data was returned for {linkedin_url}."
    except ImportError:
        return "Error: apify-client is not installed. Run `pip install apify-client`."
    except Exception as e:
        return f"Error running Apify: {str(e)}"
