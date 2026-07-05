import requests
from bs4 import BeautifulSoup
import markdownify

html = requests.get("https://in.linkedin.com/jobs/search?keywords=Python&location=Pune&geoId=112419263&distance=25&f_TPR=r604800&f_JT=F&activeFilter=f_TPR&position=1&pageNum=0").text

soup = BeautifulSoup(html, "html.parser")
for tag in soup(["script", "style", "nav", "footer", "head", "noscript", "svg", "iframe", "aside", "form"]):
    tag.decompose()

md = markdownify.markdownify(str(soup), heading_style="ATX").strip()
print(repr(md[:1000]))
