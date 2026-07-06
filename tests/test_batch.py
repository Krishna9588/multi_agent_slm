import csv
import json
from agents.batch_scraper_agent import batch_scraper_agent

urls = []
with open('archive/outputs/perfect_pune_python_jobs.csv', 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        if row['URL'].startswith('http'):
            urls.append(row['URL'])
        if len(urls) == 2:
            break

print(f"Testing batch scraper on {len(urls)} URLs...")
result = batch_scraper_agent(urls, strategy="requests", output_format="markdown", max_words_per_page=500)
print("Batch Scrape Complete.")
print("Total URLs:", result["total_urls"])
for url, data in result["results"].items():
    print(f"\n--- URL: {url[:60]}... ---")
    if "error" in data:
        print("ERROR:", data["error"])
    else:
        print("TITLE:", data["title"])
        print("TEXT:", data["text"][:300].replace('\n', ' '))

