"""
Agent: deep_research_agent
--------------------------
Performs compound, multi-page website research.
Instead of relying on the orchestrator to stitch together link extracting,
scraping, and parsing, this agent handles it all internally in a robust way.
It crawls the main page and top internal links, then makes an isolated LLM
call to synthesize the data according to the research goal.
"""

from agents.link_extractor import link_extractor
from agents.web_scraper import web_scraper
from core.models import get_conversation_session, DEFAULT_MODEL
import time

DESCRIPTION = (
    "A powerful compound agent for deep website research and comprehensive company profiling. "
    "Use this whenever you are asked to 'do in-depth research', 'crawl', 'company profile', "
    "or list comprehensive details about a company. "
    "It automatically crawls the main page and sub-pages, then synthesizes a huge JSON profile and Markdown report."
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
        "description": "The specific task or formatting you want to achieve (e.g., 'List all URLs in a structured table with their products').",
    },
    "max_sub_pages": {
        "type": "integer",
        "required": False,
        "description": "Max number of sub-pages to crawl. Default is 5.",
    }
}

def deep_research_agent(url: str, research_goal: str, max_sub_pages: int = 5) -> dict:
    """Crawls a site and synthesizes a response based on the goal."""
    
    # If the user just says "in-depth research", use the comprehensive schema
    if "in depth" in research_goal.lower() or "company profile" in research_goal.lower() or len(research_goal) < 30:
        research_goal = (
            "Extract a comprehensive company profile including: Company Name, Domain, "
            "About this company, Founding Members, Products, Services and offering, "
            "Assistant and support, Contact us details, Social media links and Mail address, "
            "About companies working and operation, their industries, Partners, Clients, "
            "Pricing, and Blogs (Title, description, author, date, content snippet)."
        )

    
    print(f"  [DeepResearch] Starting crawl on {url}")
    
    # 1. Fetch main page content
    main_page_data = web_scraper(url)
    all_text = [f"--- MAIN PAGE: {url} ---\n{main_page_data.get('text', '')}"]
    
    # 2. Extract links to find sub-pages
    links_data = link_extractor(url)
    internal_links = links_data.get("internal_links", [])
    
    # Filter and prioritize links (e.g., pricing, about, products)
    priority_keywords = ["pricing", "product", "about", "feature", "service", "contact", "blog", "team", "partner", "client"]
    
    # Sort links: those containing priority keywords first
    def sort_score(link):
        return sum(1 for kw in priority_keywords if kw in link.lower())
        
    prioritized_links = sorted(internal_links, key=sort_score, reverse=True)
    
    # Remove the main url from the list to avoid duplicate crawling
    prioritized_links = [link for link in prioritized_links if link.rstrip('/') != url.rstrip('/')]
    
    # Take top N
    target_links = prioritized_links[:max_sub_pages]
    
    print(f"  [DeepResearch] Found {len(internal_links)} internal links. Crawling top {len(target_links)} sub-pages...")
    
    # 3. Crawl sub-pages
    scraped_urls = [url]
    for sub_url in target_links:
        print(f"  [DeepResearch] Scrape -> {sub_url}")
        time.sleep(1) # Be polite
        sub_page_data = web_scraper(sub_url)
        text = sub_page_data.get('text', '')
        if text:
            all_text.append(f"--- SUB-PAGE: {sub_url} ---\n{text}")
            scraped_urls.append(sub_url)
            
    # Combine all text, truncate to protect context window (~6000 words max)
    combined_text = "\n\n".join(all_text)
    words = combined_text.split()
    if len(words) > 6000:
        combined_text = " ".join(words[:6000]) + " [...TRUNCATED DUE TO LENGTH...]"
        
    print(f"  [DeepResearch] Synthesis phase. Passing {len(words)} words to LLM...")
    
    # 4. Isolated LLM Call for Synthesis
    prompt = f"""You are an expert data synthesizer.
I have crawled multiple pages of a website for you.

RESEARCH GOAL:
{research_goal}

AVAILABLE DATA:
{combined_text}

You MUST output your response as a single, valid JSON dictionary with keys matching the requested data points.
Do not output markdown. Output ONLY valid JSON.
"""
    
    session = get_conversation_session(model=DEFAULT_MODEL)
    try:
        # Request JSON output
        response = session.chat(prompt, format="json")
        import json
        try:
            data = json.loads(response)
        except json.JSONDecodeError:
            data = {"raw": response}
            
        # Convert JSON dictionary into a readable Markdown string for the chat
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
        
        return {
            "status": "success",
            "scraped_urls": scraped_urls,
            "markdown_report": markdown_report,
            "structured_data": data
        }
    except Exception as e:
        return {
            "status": "error",
            "error_message": str(e)
        }
