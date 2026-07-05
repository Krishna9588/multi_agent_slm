from agents.web_scraper import web_scraper

url = "https://in.linkedin.com/jobs/search?keywords=Python&location=Pune&geoId=112419263&distance=25&f_TPR=r604800&f_JT=F&activeFilter=f_TPR&position=1&pageNum=0"
result = web_scraper(url, strategy="requests", output_format="markdown")
print(result["text"][:1000])
