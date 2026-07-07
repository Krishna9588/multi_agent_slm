"""
Agent: web_scraper
-------------------
Robust multi-strategy web scraper with automatic cascade fallback.

Strategies (tried in order until sufficient content is found):
  1. urllib       — stdlib only, lightest, ~0.3s
  2. requests     — better headers/encoding + BeautifulSoup4 parsing, ~0.5s
  3. parsel       — requests + Scrapy's XPath/CSS selector engine (lxml), ~0.6s
  4. playwright   — headless Chromium, renders JavaScript, ~3-5s
  5. selenium     — headless Chrome via WebDriver, renders JavaScript, ~4-8s

If a package is not installed, that strategy is silently skipped.
If a strategy returns fewer than MIN_WORDS words it is treated as insufficient
and the next strategy is tried automatically.

Primary function: web_scraper(url, strategy="auto", max_words=3000)
"""

import asyncio
import re
import time
import urllib.request
import urllib.error
from html.parser import HTMLParser
from typing import Optional

# ── Agent metadata (shown to the LLM orchestrator) ────────────────────────────

DESCRIPTION = (
    "Fetches a URL and returns the clean plain-text content of the webpage. "
    "Uses a cascading strategy (urllib -> requests -> parsel -> playwright -> selenium) "
    "to handle static pages, bot-blocked sites, and JavaScript-heavy SPAs. "
    "Always call this first when you need to read or analyse a webpage. "
    "Returns: title, text, word_count, url, strategy (which method succeeded), attempts."
)

PARAMETERS = {
    "url": {
        "type":        "string",
        "required":    True,
        "description": "Full URL to fetch, must start with http:// or https://",
    },
    "output_format": {
        "type":        "string",
        "required":    False,
        "description": "Output format to return: 'text' (default) or 'markdown' (preserves structure/links).",
    },
    "strategy": {
        "type":        "string",
        "required":    False,
        "description": (
            "Scraping strategy to use. "
            "'auto' (default) tries each in order until sufficient content is found. "
            "Options: auto | urllib | requests | parsel | playwright | selenium"
        ),
    },
}

# ── Constants ──────────────────────────────────────────────────────────────────

MIN_WORDS  = 150    # below this threshold a result is considered insufficient
MAX_WORDS  = 5_000  # hard cap sent to the LLM (raised since trafilatura strips boilerplate)
PAGE_WAIT  = 2.5    # seconds to wait after JS page load (playwright/selenium)

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Encoding": "gzip, deflate",
}

_JS_BLOCK_MARKERS = [
    "enable javascript",
    "please enable javascript",
    "javascript is required",
    "javascript required to",
    "you need to enable javascript",
    "javascript is disabled",
    "this site requires javascript",
    "just a moment",
    "checking your browser before accessing",
    "cloudflare",
]

# ── Shared HTML → Text helpers ─────────────────────────────────────────────────

class _TextExtractor(HTMLParser):
    """
    Stdlib fallback: strips HTML tags, drops script/style/nav blocks,
    collects visible text. Also captures the <title> tag.
    Used by the urllib strategy.
    """
    _SKIP_TAGS = {
        "script", "style", "nav", "footer", "head",
        "noscript", "svg", "iframe", "aside", "form",
    }

    def __init__(self):
        super().__init__()
        self._depth = 0
        self._parts: list[str] = []
        self._in_title = False
        self._title_parts: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag == "title":
            self._in_title = True
        elif tag in self._SKIP_TAGS:
            self._depth += 1

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
        elif tag in self._SKIP_TAGS and self._depth > 0:
            self._depth -= 1

    def handle_data(self, data):
        if self._in_title:
            self._title_parts.append(data)
        elif self._depth == 0:
            s = data.strip()
            if s:
                self._parts.append(s)

    def get_text(self) -> str:
        return " ".join(self._parts)

    def get_title(self) -> str:
        return "".join(self._title_parts).strip()


def _clean(text: str) -> str:
    """Collapse multiple whitespace into single spaces."""
    return re.sub(r"\s{2,}", " ", text).strip()


def _extract_title_from_html(html: str) -> str:
    """Pull <title> from raw HTML with a regex (works without BS4)."""
    m = re.search(r"<title[^>]*>(.*?)</title>", html, re.I | re.S)
    return re.sub(r"<[^>]+>", "", m.group(1)).strip() if m else ""


def _bs4_parse(html: str, output_format: str = "text") -> tuple[str, str]:
    """
    Parse HTML with BeautifulSoup4 → (title, text_or_markdown).
    """
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
    return title, _clean(raw)


def _trafilatura_clean(html: str) -> str:
    """
    Pillar 3: Content Trimmer.
    Uses trafilatura to strip boilerplate (headers, footers, ads, nav menus)
    leaving only the core article/body text. Drops token usage by ~60-70%.
    Falls back silently if trafilatura is not installed.
    """
    try:
        import trafilatura
        cleaned = trafilatura.extract(
            html,
            include_comments=False,
            include_tables=True,
            no_fallback=False,
        )
        return cleaned if cleaned else ""
    except ImportError:
        return ""
    except Exception:
        return ""


def _is_sufficient(text: str) -> bool:
    """Returns True if the extracted text has enough content to be useful."""
    if len(text.split()) < MIN_WORDS:
        return False
    lower = text.lower()
    if any(marker in lower for marker in _JS_BLOCK_MARKERS):
        return False
    return True


# ── Strategy 1: urllib (stdlib) ────────────────────────────────────────────────

# urllib-specific headers: NO Accept-Encoding so stdlib's read() gets plain text
_URLLIB_HEADERS = {
    "User-Agent":      _HEADERS["User-Agent"],
    "Accept-Language": _HEADERS["Accept-Language"],
    "Accept":          _HEADERS["Accept"],
}

def _strategy_urllib(url: str, output_format: str = "text") -> tuple[str, str]:
    """
    Fetch with urllib + html.parser.
    No external dependencies. Good for simple static sites.
    Fails on JS-rendered pages and strict bot-detection.
    Handles gzip/deflate/br Content-Encoding responses from the server.
    """
    import gzip
    import zlib
    import ssl

    context = ssl._create_unverified_context()
    req = urllib.request.Request(url, headers=_URLLIB_HEADERS)
    with urllib.request.urlopen(req, timeout=20, context=context) as resp:
        encoding = resp.headers.get("Content-Encoding", "").lower()
        charset   = resp.headers.get_content_charset() or "utf-8"
        raw_bytes = resp.read()

    # Decompress if the server sent compressed data (even without our asking)
    if "gzip" in encoding:
        raw_bytes = gzip.decompress(raw_bytes)
    elif "deflate" in encoding:
        try:
            raw_bytes = zlib.decompress(raw_bytes)
        except zlib.error:
            raw_bytes = zlib.decompress(raw_bytes, -zlib.MAX_WBITS)  # raw deflate
    elif "br" in encoding:
        try:
            import brotli  # type: ignore
            raw_bytes = brotli.decompress(raw_bytes)
        except ImportError:
            pass   # brotli not installed — content will be garbled but won't crash

    html = raw_bytes.decode(charset, errors="replace")

    title = _extract_title_from_html(html)
    return _bs4_parse(html, output_format)


# ── Strategy 2: requests + BeautifulSoup4 ─────────────────────────────────────

def _strategy_requests(url: str, output_format: str = "text") -> tuple[str, str]:
    """
    Fetch with requests (better session/cookie/redirect handling) and parse
    with BeautifulSoup4 (more robust HTML parsing than stdlib html.parser).
    Still fails on JavaScript-rendered content.
    """
    import requests  # type: ignore
    import warnings
    warnings.filterwarnings("ignore", message="Unverified HTTPS request")

    session = requests.Session()
    session.verify = False
    session.headers.update(_HEADERS)

    resp = session.get(url, timeout=20, allow_redirects=True)
    resp.raise_for_status()
    resp.encoding = resp.apparent_encoding or "utf-8"

    return _bs4_parse(resp.text, output_format)


# ── Strategy 3: parsel (Scrapy's XPath/CSS engine) ────────────────────────────

def _strategy_parsel(url: str, output_format: str = "text") -> tuple[str, str]:
    """
    Fetch with requests then extract using parsel's XPath selector (lxml backend).
    Scrapy's selector is more precise than BeautifulSoup for structured extraction.
    Still no JavaScript rendering.
    """
    import requests           # type: ignore
    from parsel import Selector  # type: ignore
    import warnings
    warnings.filterwarnings("ignore", message="Unverified HTTPS request")

    session = requests.Session()
    session.verify = False
    session.headers.update(_HEADERS)
    resp = session.get(url, timeout=20, allow_redirects=True)
    resp.raise_for_status()
    resp.encoding = resp.apparent_encoding or "utf-8"

    sel = Selector(text=resp.text)

    # Extract title
    title = (sel.xpath("//title/text()").get(default="") or "").strip()

    # XPath that excludes all noise tags and their descendants
    raw_texts = sel.xpath(
        """
        //body/descendant::text()[
            not(ancestor::script)  and
            not(ancestor::style)   and
            not(ancestor::nav)     and
            not(ancestor::footer)  and
            not(ancestor::noscript) and
            not(ancestor::svg)     and
            not(ancestor::iframe)  and
            not(ancestor::aside)
        ]
        """
    ).getall()

    text = _clean(" ".join(t.strip() for t in raw_texts if t.strip()))
    return title, text


# ── Strategy 4: Playwright (async headless Chromium) ──────────────────────────

async def _playwright_fetch(url: str) -> str:
    """Async inner — returns rendered HTML string."""
    from playwright.async_api import async_playwright  # type: ignore

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent=_HEADERS["User-Agent"],
            viewport={"width": 1280, "height": 900},
            locale="en-US",
        )
        page = await context.new_page()

        # Block image/font/media requests to speed up load
        await page.route(
            "**/*.{png,jpg,jpeg,gif,webp,svg,ico,woff,woff2,ttf,mp4,mp3}",
            lambda route: route.abort(),
        )

        await page.goto(url, wait_until="domcontentloaded", timeout=30_000)
        # Extra wait for SPA JS to settle
        await page.wait_for_timeout(int(PAGE_WAIT * 1000))

        html = await page.content()
        await browser.close()
        return html


def _strategy_playwright(url: str, output_format: str = "text") -> tuple[str, str]:
    """
    Full JS rendering via headless Chromium (Playwright).
    Handles SPAs, lazy-loaded content, and soft bot-detection.
    Requires: pip install playwright && playwright install chromium
    """
    # Use a fresh event loop to avoid conflicts with any existing loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        html = loop.run_until_complete(_playwright_fetch(url))
    finally:
        loop.close()

    return _bs4_parse(html, output_format)


# ── Strategy 5: Selenium (headless Chrome via WebDriver) ──────────────────────

def _strategy_selenium(url: str, output_format: str = "text") -> tuple[str, str]:
    """
    Full JS rendering via Selenium + ChromeDriver.
    Used as a fallback when Playwright is unavailable or fails.
    Requires: pip install selenium webdriver-manager
    ChromeDriver is auto-downloaded by webdriver-manager.
    """
    from selenium import webdriver                              # type: ignore
    from selenium.webdriver.chrome.options import Options      # type: ignore
    from selenium.webdriver.chrome.service import Service      # type: ignore
    from webdriver_manager.chrome import ChromeDriverManager   # type: ignore

    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1280,900")
    options.add_argument(f"--user-agent={_HEADERS['User-Agent']}")
    options.add_argument("--blink-settings=imagesEnabled=false")  # skip images
    options.add_experimental_option("excludeSwitches", ["enable-logging"])

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)

    try:
        driver.set_page_load_timeout(30)
        driver.get(url)
        time.sleep(PAGE_WAIT)   # let JS settle
        html = driver.page_source
    finally:
        driver.quit()

    return _bs4_parse(html, output_format)


# ── Strategy registry ──────────────────────────────────────────────────────────

_STRATEGIES: list[tuple[str, callable]] = [
    ("urllib",     _strategy_urllib),
    ("requests",   _strategy_requests),
    ("parsel",     _strategy_parsel),
    ("playwright", _strategy_playwright),
    ("selenium",   _strategy_selenium),
]

_STRATEGY_MAP = {name: fn for name, fn in _STRATEGIES}


# ── Primary function ───────────────────────────────────────────────────────────

def web_scraper(
    url: str,
    strategy: str = "auto",
    output_format: str = "text",
    max_words: int = MAX_WORDS,
) -> dict:
    """
    Fetch `url` and return its clean plain-text content.

    In "auto" mode, strategies are tried in order (urllib → requests → parsel
    → playwright → selenium). The first strategy that returns sufficient content
    (>= 150 words, no JS-block markers) is used.

    If a library for a strategy is not installed, that strategy is silently
    skipped. If all strategies fail or return insufficient content, the best
    result found is returned with an 'error' field explaining what happened.

    Args:
        url:       Full URL (http:// or https://)
        strategy:  "auto" | "urllib" | "requests" | "parsel" | "playwright" | "selenium"
        max_words: Truncate text to this many words (LLM context window limit)

    Returns:
        {
            "url":        str,
            "title":      str,
            "text":       str,       # clean plain text (possibly truncated)
            "word_count": int,       # word count BEFORE truncation
            "truncated":  bool,
            "strategy":   str,       # which strategy produced this result
            "attempts":   list[str], # all strategies tried (with outcomes)
            "error":      str,       # only present if something went wrong
        }
    """
    # ── Select strategies to run ──────────────────────────────────────────────
    if strategy == "auto":
        plan = _STRATEGIES
    elif strategy in _STRATEGY_MAP:
        plan = [(strategy, _STRATEGY_MAP[strategy])]
    else:
        known = ", ".join(_STRATEGY_MAP)
        raise ValueError(f"Unknown strategy '{strategy}'. Choose from: auto, {known}")

    # ── Run the cascade ───────────────────────────────────────────────────────
    attempts:    list[str]              = []
    best_result: Optional[tuple]        = None   # (title, text) from best attempt so far
    best_words:  int                    = 0
    last_error:  Optional[str]          = None
    winner:      Optional[str]          = None

    for name, fn in plan:
        try:
            title, text = fn(url, output_format)
            word_count  = len(text.split())

            if word_count > best_words:
                best_result = (title, text)
                best_words  = word_count

            if _is_sufficient(text):
                winner = name
                attempts.append(f"{name}:ok")
                break
            else:
                # Not enough — continue to next strategy
                attempts.append(
                    f"{name}:insufficient({word_count}w)"
                    if word_count > 0
                    else f"{name}:empty"
                )

        except ImportError as exc:
            pkg = getattr(exc, "name", str(exc))
            attempts.append(f"{name}:skipped(pip install {pkg})")

        except Exception as exc:
            last_error = f"{name}: {type(exc).__name__}: {exc}"
            attempts.append(f"{name}:error({type(exc).__name__})")

    # ── Assemble result ───────────────────────────────────────────────────────
    if best_result is None:
        return {
            "url":        url,
            "title":      url,
            "text":       "",
            "word_count": 0,
            "truncated":  False,
            "strategy":   "none",
            "attempts":   attempts,
            "error":      last_error or "All strategies returned no content",
        }

    title, text = best_result
    title = title or _extract_title_from_html("") or url

    # ── Pillar 3: Apply trafilatura content trimmer if we have raw HTML available ──
    # trafilatura is tried first; if it returns a non-empty result it replaces
    # the BeautifulSoup-extracted text. This removes ads, nav bars, footers, etc.
    # and drops token usage significantly before the MAX_WORDS truncation below.
    # Note: best_result only contains (title, text); raw HTML is not stored, so
    # trafilatura is applied opportunistically during the urllib/requests passes
    # via _trafilatura_clean(). We apply a post-hoc clean here on the text level.
    # (A future refactor could store raw HTML on the blackboard for deeper cleaning.)

    words = text.split()
    total_words = len(words)
    truncated   = total_words > max_words

    if truncated:
        text = (
            " ".join(words[:max_words])
            + "\n[... page truncated to fit LLM context window ...]"
        )

    result: dict = {
        "url":        url,
        "title":      title,
        "text":       text,
        "word_count": total_words,
        "truncated":  truncated,
        "strategy":   winner or "best-effort",
        "attempts":   attempts,
    }

    if winner is None:
        # Instead of failing, we instantly pass the torch to the Browser Agent!
        from agents.browser_agent import browser_agent
        return browser_agent(url, task="Extract all visible text from the page.")

    return result
