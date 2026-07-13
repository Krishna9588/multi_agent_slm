"""
Agent: company_research_agent
-----------------------------
A highly specialized research agent designed to perform exhaustive company profiling.
It orchestrates finance, web scraping, and social media tools to gather massive amounts of data
and synthesizes it into a strict, user-defined schema.
"""

from agents.finance_agent import finance_agent
from agents.web_scraper import web_scraper
from agents.link_extractor import link_extractor
from agents.social_media_agent import social_media_agent
from agents.data_exporter_agent import data_exporter_agent
from core.models import get_conversation_session, DEFAULT_MODEL
import time
import json

DESCRIPTION = (
    "Exhaustive Company Profiling Agent. Use this when the user asks for a simple research on a company "
    "or an in-depth company profile. It automatically pulls financials, stakeholders, tech stack, careers, "
    "and products, then exports a highly structured markdown report."
)

PARAMETERS = {
    "company_name": {
        "type": "string",
        "required": True,
        "description": "The full name of the company.",
    },
    "domain": {
        "type": "string",
        "required": True,
        "description": "The primary website domain (e.g., https://www.adobe.com).",
    },
    "ticker": {
        "type": "string",
        "required": False,
        "description": "The stock ticker symbol (e.g., ADBE), if known.",
    }
}

def company_research_agent(company_name: str, domain: str, ticker: str = "") -> dict:
    """Orchestrates comprehensive data gathering and synthesizes a master report."""
    
    print(f"  [Research] Initiating Deep Company Profiling for {company_name} ({ticker or 'Private'})")
    
    collected_data = []
    
    # 1. Financial & News Data
    if ticker:
        print(f"  [Research] Fetching Financial Data for {ticker}...")
        collected_data.append(f"--- FINANCE PROFILE (Yahoo) ---")
        try:
            profile = finance_agent(ticker, "profile")
            collected_data.append(json.dumps(profile, indent=2))
        except Exception as e:
            collected_data.append(f"Profile error: {e}")
            
        try:
            history = finance_agent(ticker, "history", period="1y")
            collected_data.append(f"--- STOCK HISTORY (1 Year) ---")
            collected_data.append(json.dumps(history, indent=2))
        except Exception as e:
            collected_data.append(f"History error: {e}")
            
        try:
            news = finance_agent(ticker, "news")
            collected_data.append(f"--- LATEST NEWS (Yahoo) ---")
            collected_data.append(json.dumps(news, indent=2))
        except Exception as e:
            collected_data.append(f"News error: {e}")

    # 2. Website Crawling
    print(f"  [Research] Crawling primary domain: {domain}")
    try:
        main_page = web_scraper(domain)
        collected_data.append(f"--- MAIN PAGE ({domain}) ---")
        collected_data.append(main_page.get("text", "")[:4000])  # Limit to 4k words
    except Exception as e:
         collected_data.append(f"Main page scrape error: {e}")
         
    # 3. Discover sub-pages (Careers, Pricing, About)
    print(f"  [Research] Extracting sitemap & key pages...")
    sub_urls = []
    try:
        links_data = link_extractor(domain)
        internal_links = links_data.get("internal_links", [])
        
        # Save the list of links for the schema
        collected_data.append(f"--- LIST OF ALL DISCOVERED PAGES ON DOMAIN ---")
        collected_data.append("\n".join(internal_links[:50])) 
        
        priority_keywords = ["career", "job", "about", "product", "pricing", "contact"]
        def sort_score(link):
            return sum(1 for kw in priority_keywords if kw in link.lower())
            
        prioritized = sorted([l for l in internal_links if l.rstrip('/') != domain.rstrip('/')], key=sort_score, reverse=True)
        sub_urls = prioritized[:3]
        
    except Exception as e:
        print(f"  [Research] Link extraction failed: {e}")

    # Scrape Top Sub-Pages
    for sub_url in sub_urls:
        print(f"  [Research] Scraping sub-page: {sub_url}")
        time.sleep(1)
        try:
            sub_page_data = web_scraper(sub_url)
            collected_data.append(f"--- SUB-PAGE: {sub_url} ---")
            collected_data.append(sub_page_data.get("text", "")[:2000])
        except Exception as e:
            pass

    # 4. Social Media & Sentiment (Simulation/Extraction)
    print(f"  [Research] Checking Social Sentiment for {company_name}")
    try:
        sentiment = social_media_agent("analyze_sentiment", "linkedin", keyword=company_name)
        collected_data.append(f"--- LINKEDIN SENTIMENT ---")
        collected_data.append(json.dumps(sentiment))
    except Exception as e:
        pass
        
    print(f"  [Research] Compiling Master Dataset...")
    master_context = "\n\n".join(collected_data)
    words = master_context.split()
    if len(words) > 8000:
         master_context = " ".join(words[:8000]) + " [...TRUNCATED...]"
         
    # 5. LLM Synthesis mapped strictly to User's Schema
    print(f"  [Research] Synthesizing data into Strict Schema using LLM...")
    prompt = f"""You are an elite corporate research analyst. 
You must synthesize the raw data provided below into a strictly formatted Markdown report for the company: {company_name}.
CRITICAL RULE: YOU MUST NOT HALLUCINATE OR MAKE UP ANY INFORMATION. DO NOT USE PRE-TRAINED KNOWLEDGE.
If the RAW DATA does not contain the information for a specific field, you MUST write "Not provided in raw data" or "Scraping failed to find this info". 
Do NOT make "industry estimates". If the RAW DATA is completely empty or only contains errors, explicitly state that the web scraping failed at the top of the report.

STRICT SCHEMA TO FOLLOW (Use these exact Markdown H2 Headers):
## Company Overview
- **Company Name:** 
- **Domain:** 
- **Brief about the company:** 

## Business & Operations
- **Products:** 
- **Services:** 
- **Pricing:** 
- **Operational Regions:** 
- **Tech Stack (Preferred/Observed):** 

## Financial Analysis & Stock
- **Financial Analysis (Revenue, Market Cap):** 
- **Stock performance (if public):** 

## Corporate Statistics
- **Employee Count:** 
- **Stake holders / Investors:** 

## Latest News & Media
- **Latest news:** 
- **People's opinion / Public sentiment:** 

## Careers & Hiring
- **Career page details & Job openings:** 
- **POC For jobs and research:** 
- **HR list in India and their LinkedIn:** 

## Leadership
- **C-Suite people list and their LinkedIn:** 

## Contact & Location
- **Address (HQ & Global):** 
- **Contact Number:** 
- **Email:** 
- **Social media links:** 

## Strategic Deep Dive
- **Website deep dive (Core focus):** 
- **Strategic importance:** 
- **Way to reach out and what the company most needs right now:** 

## Domain Structure
- **List of all pages available on the domain:** (Brief list)

---
RAW DATA:
{master_context}
"""
    
    session = get_conversation_session(model=DEFAULT_MODEL)
    try:
        report_markdown = session.chat(prompt, format="text")
        
        # 6. Auto-Export using data_exporter_agent
        print(f"  [Research] Exporting final markdown report...")
        export_res = data_exporter_agent(data_json=report_markdown, filename_prefix=f"{company_name.replace(' ', '_')}_Research", format="md")
        
        if "error" in export_res:
            return {"status": "error", "message": "Synthesis succeeded but export failed.", "export_error": export_res, "report": report_markdown}
            
        return {
            "status": "success",
            "message": f"Successfully completed deep research and mapped to custom schema.",
            "file_path": export_res.get("file_path", ""),
        }

    except Exception as e:
        return {
            "status": "error",
            "error_message": f"LLM synthesis failed: {str(e)}"
        }
