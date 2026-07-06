import json
from agents.web_scraper import web_scraper
from agents.data_structuring_agent import data_structuring_agent

print("1. Fetching single job page...")
url = "https://in.linkedin.com/jobs/view/jr-python-developer-at-zensar-technologies-4433683153"
res = web_scraper(url, strategy="requests", output_format="markdown")
md = res["text"]

print("2. Running Data Structuring Agent...")
structured = data_structuring_agent(md[:2000], context="LinkedIn Job Posting")

print("--- RESULTS ---")
print("Status:", structured.get("status"))
print("Schema Discovered:", structured.get("schema"))
print("Data Extracted:\n", json.dumps(structured.get("data"), indent=2))
