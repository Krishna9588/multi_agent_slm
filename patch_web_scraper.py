import re

with open('agents/web_scraper.py', 'r') as f:
    code = f.read()

# 1. Update PARAMETERS
params_old = """    "strategy": {"""
params_new = """    "output_format": {
        "type":        "string",
        "required":    False,
        "description": "Output format to return: 'text' (default) or 'markdown' (preserves structure/links).",
    },
    "strategy": {"""
code = code.replace(params_old, params_new)

# 2. Update _bs4_parse
bs4_old = """def _bs4_parse(html: str) -> tuple[str, str]:
    \"\"\"
    Parse HTML with BeautifulSoup4 → (title, plain_text).
    Removes script/style/nav/footer before extracting text.
    \"\"\"
    from bs4 import BeautifulSoup  # type: ignore

    soup = BeautifulSoup(html, "html.parser")

    title_tag = soup.find("title")
    title = title_tag.get_text().strip() if title_tag else ""

    for tag in soup(["script", "style", "nav", "footer", "head",
                     "noscript", "svg", "iframe", "aside", "form"]):
        tag.decompose()

    raw = soup.get_text(separator=" ", strip=True)
    return title, _clean(raw)"""

bs4_new = """def _bs4_parse(html: str, output_format: str = "text") -> tuple[str, str]:
    \"\"\"
    Parse HTML with BeautifulSoup4 → (title, text_or_markdown).
    \"\"\"
    from bs4 import BeautifulSoup  # type: ignore

    soup = BeautifulSoup(html, "html.parser")

    title_tag = soup.find("title")
    title = title_tag.get_text().strip() if title_tag else ""

    for tag in soup(["script", "style", "nav", "footer", "head",
                     "noscript", "svg", "iframe", "aside", "form"]):
        tag.decompose()

    if output_format == "markdown":
        try:
            import markdownify
            return title, markdownify.markdownify(str(soup), heading_style="ATX").strip()
        except ImportError:
            pass

    raw = soup.get_text(separator=" ", strip=True)
    return title, _clean(raw)"""
code = code.replace(bs4_old, bs4_new)

# 3. Update urllib
url_old = """    extractor = _TextExtractor()
    extractor.feed(html)

    title = extractor.get_title() or _extract_title_from_html(html)
    text  = _clean(extractor.get_text())

    return title, text"""

url_new = """    title = _extract_title_from_html(html)
    return _bs4_parse(html, output_format)"""
code = re.sub(r'def _strategy_urllib\(url: str\) -> tuple\[str, str\]:', 'def _strategy_urllib(url: str, output_format: str = "text") -> tuple[str, str]:', code)
code = code.replace(url_old, url_new)

# 4. Update other strategies signatures and _bs4_parse calls
for fn in ['_strategy_requests', '_strategy_parsel', '_strategy_playwright', '_strategy_selenium']:
    code = re.sub(fr'def {fn}\(url: str\) -> tuple\[str, str\]:', fr'def {fn}(url: str, output_format: str = "text") -> tuple[str, str]:', code)

code = re.sub(r'return _bs4_parse\(html\)', 'return _bs4_parse(html, output_format)', code)

# 5. Update primary function
code = re.sub(r'def web_scraper\(\n    url: str,\n    strategy: str = "auto",\n    max_words: int = MAX_WORDS,\n\) -> dict:',
              'def web_scraper(\n    url: str,\n    strategy: str = "auto",\n    output_format: str = "text",\n    max_words: int = MAX_WORDS,\n) -> dict:', code)

code = re.sub(r'title, text = fn\(url\)', 'title, text = fn(url, output_format)', code)

with open('agents/web_scraper.py', 'w') as f:
    f.write(code)
print("Patched successfully")
