import json
from agents.web_scraper import web_scraper
from agents.batch_scraper_agent import batch_scraper_agent
from agents.data_exporter_agent import data_exporter_agent

url = "https://in.linkedin.com/jobs/search?keywords=Python&location=Pune&geoId=112419263&distance=25&f_TPR=r604800&f_JT=F&activeFilter=f_TPR&position=1&pageNum=0"
search_res = web_scraper(url, strategy="requests", output_format="markdown")

urls = []
job_blocks = search_res["text"].split('* [')
for block in job_blocks[1:]:
    try:
        title_end = block.find(']')
        link_start = block.find('(', title_end)
        link_end = block.find(')', link_start)
        job_link = block[link_start+1:link_end]
        if job_link.startswith("http"):
            urls.append(job_link)
    except Exception:
        pass

urls = urls[:10]
deep_results = batch_scraper_agent(urls, strategy="requests", output_format="markdown", max_words_per_page=800)

final_jobs = []
for job_url, data in deep_results["results"].items():
    if "error" in data:
        continue
    text = data.get("text", "")
    title = data.get("title", "")
    detailed_desc = text.replace('\n', ' ').strip()
    final_jobs.append({
        "URL": job_url,
        "Page Title": title[:100],
        "Detailed Segment": detailed_desc[:500] + "..."
    })

res = data_exporter_agent(
    data_json=json.dumps(final_jobs),
    format="csv",
    filename_prefix="pune_python_jobs_detailed",
    export_formats="csv"
)
print("Pipeline Complete!", res)
