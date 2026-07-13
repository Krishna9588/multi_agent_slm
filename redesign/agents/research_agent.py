import re
import json
from redesign.core.state import AgentState
from redesign.core.tools import robust_web_scraper, get_internal_links, apify_linkedin_scraper

def research_agent(state: AgentState) -> dict:
    """
    The Deterministic Research Agent node.
    It extracts targets (URLs, LinkedIn handles) from the prompt using pure Python,
    and runs the extraction tools directly. No LLM loop.
    """
    print("--- [Research Agent] Starting Deterministic Data Gathering ---")
    
    task_prompt = state.get("task_prompt", "")
    raw_data = state.get("raw_data", {})
    
    # 1. Extract Website URLs
    url_pattern = re.compile(r"https?://(?:www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b(?:[-a-zA-Z0-9()@:%_\+.~#?&//=]*)")
    found_urls = url_pattern.findall(task_prompt)
    
    # Filter for main website (ignore linkedin here)
    main_urls = [u for u in found_urls if "linkedin.com" not in u.lower()]
    if main_urls:
        target_url = main_urls[0]
        print(f"[Research Agent] Found target website: {target_url}")
        
        # Scrape main page
        print(f"[Research Agent] Scraping {target_url}...")
        main_text = robust_web_scraper.invoke({"url": target_url})
        raw_data["website_content"] = main_text
        
        # Optionally get 1-2 subpages
        sub_links = get_internal_links.invoke({"url": target_url})
        if isinstance(sub_links, list) and sub_links:
            # just take the first two meaningful links like 'about' or 'contact'
            for link in sub_links[:2]:
                print(f"[Research Agent] Scraping sub-page {link}...")
                sub_text = robust_web_scraper.invoke({"url": link})
                raw_data[f"subpage_{link}"] = sub_text
    
    # 2. Extract LinkedIn URLs
    # Look for full URLs or "linkedin.com/in/..."
    linkedin_pattern = re.compile(r"(?:https?://)?(?:www\.)?linkedin\.com/(?:in|company)/[a-zA-Z0-9_-]+")
    linkedin_matches = linkedin_pattern.findall(task_prompt)
    
    for li_url in linkedin_matches:
        if not li_url.startswith("http"):
            li_url = "https://" + li_url
        print(f"[Research Agent] Scraping LinkedIn: {li_url}")
        li_data = apify_linkedin_scraper.invoke({"linkedin_url": li_url})
        raw_data[f"linkedin_{li_url}"] = li_data

    # Compile the final summary for the analysis agent
    summary = "=== RAW SCRAPED DATA ===\n"
    for source, content in raw_data.items():
        summary += f"\n--- SOURCE: {source} ---\n{content[:5000]}\n"  # limit context to 5000 chars per source
        
    raw_data["research_summary"] = summary
    
    print("--- [Research Agent] Finished Data Gathering ---")
    
    return {
        "raw_data": raw_data
    }

def main():
    """Standalone test function for the deterministic research agent."""
    print("Testing Research Agent directly...")
    dummy_state = {
        "task_prompt": "Research eChai Ventures. Website: https://echai.ventures/ Contact Method: linkedin.com/in/jatinchaudhary.",
        "messages": [],
        "raw_data": {},
        "structured_data": {},
        "report_path": "",
        "errors": []
    }
    result = research_agent(dummy_state)
    print("\nResult Keys gathered:")
    print(result["raw_data"].keys())
    print("\nSnippet of summary:")
    print(result["raw_data"]["research_summary"][:500])

if __name__ == "__main__":
    main()
