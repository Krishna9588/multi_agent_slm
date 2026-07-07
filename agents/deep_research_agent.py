"""
Agent: deep_research_agent
--------------------------
Performs compound, multi-page website research concurrently.
It crawls the main page, uses an LLM to select the most relevant internal links
based on the research goal, fetches them concurrently using ThreadPoolExecutor,
and synthesizes the data.
"""

from agents.link_extractor import link_extractor
from agents.web_scraper import web_scraper
from core.models import get_conversation_session, DEFAULT_MODEL
import time
import json
from concurrent.futures import ThreadPoolExecutor, as_completed

DESCRIPTION = (
    "A powerful compound agent for deep website research and comprehensive company profiling. "
    "Use this whenever you are asked to 'do in-depth research', 'crawl', 'company profile', "
    "or list comprehensive details about a company. "
    "It automatically crawls the main page and sub-pages concurrently, then synthesizes a JSON profile and Markdown report."
)

PARAMETERS = {
    "url": {
        "type": "string",
        "required": True,
        "description": "The root URL of the website to research.",
    },
    "research_goal": {
        "type": "string",
        "required": True,
        "description": "The specific task or formatting you want to achieve.",
    },
    "max_sub_pages": {
        "type": "integer",
        "required": False,
        "description": "Max number of sub-pages to crawl. Default is 5.",
    }
}

def deep_research_agent(url: str, research_goal: str, max_sub_pages: int = 5) -> dict:
    """Crawls a site concurrently and synthesizes a response based on the goal."""
    
    if "in depth" in research_goal.lower() or "company profile" in research_goal.lower() or len(research_goal) < 30:
        research_goal = (
            "Extract a comprehensive company profile including: Company Name, Domain, "
            "About this company, Founding Members, Products, Services, "
            "Contact details, Social media links, Industries, Partners, Clients, "
            "Pricing, and Blogs."
        )

    print(f"  [DeepResearch] Starting concurrent crawl on {url}")
    
    # 1. Fetch main page content
    main_page_data = web_scraper(url)
    all_text = [f"--- MAIN PAGE: {url} ---\n{main_page_data.get('text', '')}"]
    
    # 2. Extract links
    links_data = link_extractor(url)
    internal_links = list(set([link for link in links_data.get("internal_links", []) if link.rstrip('/') != url.rstrip('/')]))
    
    print(f"  [DeepResearch] Found {len(internal_links)} unique internal links.")
    
    target_links = []
    if internal_links:
        # Intelligent Link Selection via LLM
        print(f"  [DeepResearch] Asking LLM to select top {max_sub_pages} relevant links...")
        prompt = f"""You are an intelligent web crawler. Your goal is: "{research_goal}".
Given the following list of URLs found on the homepage, select up to {max_sub_pages} URLs that are MOST likely to contain information relevant to the goal.
Respond with ONLY a valid JSON list of strings (the URLs). No markdown, no explanations.

URLs:
{json.dumps(internal_links[:50], indent=2)}"""
        
        session = get_conversation_session(model=DEFAULT_MODEL, system_prompt="You only output a JSON list of strings.")
        try:
            response = session.chat(prompt, format="json")
            # Cleanup markdown backticks if present
            response = response.strip()
            if response.startswith("```"):
                import re
                m = re.search(r"```(?:json)?\s*(\[[\s\S]*\])\s*```", response)
                if m:
                    response = m.group(1)
            
            selected_links = json.loads(response)
            if isinstance(selected_links, list):
                # Ensure they are valid URLs from our original list
                target_links = [l for l in selected_links if l in internal_links][:max_sub_pages]
        except Exception as e:
            print(f"  [DeepResearch] Intelligent link selection failed: {e}. Falling back to simple heuristic.")
            # Fallback heuristic
            priority_keywords = ["pricing", "product", "about", "service", "contact", "team"]
            def sort_score(l): return sum(1 for kw in priority_keywords if kw in l.lower())
            target_links = sorted(internal_links, key=sort_score, reverse=True)[:max_sub_pages]
    
    if not target_links:
        print("  [DeepResearch] No relevant sub-pages found. Proceeding with main page only.")
    else:
        print(f"  [DeepResearch] Concurrently crawling {len(target_links)} sub-pages: {target_links}")
    
    # 3. Concurrent Crawling of sub-pages
    scraped_urls = [url]
    
    def fetch_page(sub_url):
        print(f"    [DeepResearch Worker] Scraping -> {sub_url}")
        return sub_url, web_scraper(sub_url)
        
    with ThreadPoolExecutor(max_workers=min(len(target_links) or 1, 5)) as executor:
        future_to_url = {executor.submit(fetch_page, u): u for u in target_links}
        for future in as_completed(future_to_url):
            sub_url, sub_page_data = future.result()
            text = sub_page_data.get('text', '')
            if text:
                all_text.append(f"--- SUB-PAGE: {sub_url} ---\n{text}")
                scraped_urls.append(sub_url)
            
    combined_text = "\n\n".join(all_text)
    words = combined_text.split()
    if len(words) > 8000:
        combined_text = " ".join(words[:8000]) + " [...TRUNCATED...]"
        
    print(f"  [DeepResearch] Synthesis phase. Passing {len(words)} words to LLM...")
    
    # 4. Isolated LLM Call for Synthesis
    prompt = f"""You are an expert data synthesizer.
I have crawled multiple pages of a website for you.

RESEARCH GOAL:
{research_goal}

AVAILABLE DATA:
{combined_text}

CRITICAL RULE: YOU MUST NOT HALLUCINATE OR MAKE UP ANY INFORMATION. DO NOT USE PRE-TRAINED KNOWLEDGE.
If the AVAILABLE DATA is missing information for a requested field, output "Not found in scraped data" for that field. 
If the AVAILABLE DATA is completely empty or just shows errors, return a JSON object indicating that the scraping failed.

You MUST output your response as a single, valid JSON dictionary with keys matching the requested data points.
Do not output markdown. Output ONLY valid JSON.
"""
    
    session = get_conversation_session(model=DEFAULT_MODEL)
    try:
        response = session.chat(prompt, format="json")
        try:
            data = json.loads(response.strip().strip("```json").strip("```"))
        except json.JSONDecodeError:
            data = {"raw": response}
            
        md_lines = [f"# In-Depth Research Report for {url}\n"]
        for k, v in data.items():
            md_lines.append(f"### {k.replace('_', ' ').title()}")
            if isinstance(v, list):
                for item in v:
                    md_lines.append(f"- {item}")
            elif isinstance(v, dict):
                for sub_k, sub_v in v.items():
                    md_lines.append(f"- **{sub_k}**: {sub_v}")
            else:
                md_lines.append(str(v))
            md_lines.append("")
            
        markdown_report = "\n".join(md_lines)
        
        # Save to disk automatically
        import os
        from urllib.parse import urlparse
        
        domain = urlparse(url).netloc.replace("www.", "")
        output_dir = os.path.join(os.getcwd(), "archive", "outputs")
        os.makedirs(output_dir, exist_ok=True)
        
        md_file = os.path.join(output_dir, f"{domain}_profile.md")
        json_file = os.path.join(output_dir, f"{domain}_profile.json")
        
        with open(md_file, "w", encoding="utf-8") as f:
            f.write(markdown_report)
            
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
            
        markdown_report += f"\n\n*(Results automatically saved to {md_file} and {json_file})*"
        
        return {
            "status": "success",
            "scraped_urls": scraped_urls,
            "markdown_report": markdown_report,
            "structured_data": data,
            "saved_files": [md_file, json_file]
        }
    except Exception as e:
        return {
            "status": "error",
            "error_message": str(e)
        }
