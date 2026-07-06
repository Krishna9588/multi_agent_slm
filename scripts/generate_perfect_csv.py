import csv
import re
from agents.web_scraper import web_scraper

url = "https://in.linkedin.com/jobs/search?keywords=Python&location=Pune&geoId=112419263&distance=25&f_TPR=r604800&f_JT=F&activeFilter=f_TPR&position=1&pageNum=0"
result = web_scraper(url, strategy="requests", output_format="markdown")
md = result["text"]

# Parse the markdown list
jobs = []
# Each job starts with `* [Title](JobLink)`
# followed by `### Title` and `#### [Company](CompanyLink)`

job_blocks = md.split('* [')
for block in job_blocks[1:]:
    try:
        # Get Job Title and Link
        title_end = block.find(']')
        link_start = block.find('(', title_end)
        link_end = block.find(')', link_start)
        job_title = block[:title_end]
        job_link = block[link_start+1:link_end]

        # Get Company
        company_idx = block.find('#### [')
        if company_idx != -1:
            c_title_end = block.find(']', company_idx)
            company_name = block[company_idx+6:c_title_end]
        else:
            company_name = "Unknown"
        
        # Get location / time
        # Location is usually right after the company
        rest = block[c_title_end:].split('\n')
        location = ""
        for line in rest:
            line = line.strip()
            if "India" in line or "Pune" in line:
                location = line
                break

        jobs.append({
            'Job Title': job_title,
            'Company': company_name,
            'Location': location,
            'URL': job_link
        })
    except Exception as e:
        pass

with open('archive/outputs/perfect_pune_python_jobs.csv', 'w', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=['Job Title', 'Company', 'Location', 'URL'])
    writer.writeheader()
    for job in jobs[:10]:
        writer.writerow(job)

print("Saved perfect CSV")
