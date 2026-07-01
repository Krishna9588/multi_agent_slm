"""
Multi-Agent Web Analysis Workflow
-----------------------------------
Fetches any URL, strips HTML to plain text, then runs 4 specialised AI
agents powered by llama3.1:8b via Ollama:

  1. Page Classifier  — identifies page type (home / about-us / careers / etc.)
  2. NER Agent        — extracts people, orgs, locations, products, technologies
  3. Topic Modeling   — finds primary topic, themes, keywords, one-line summary
  4. Sentiment Agent  — analyses overall tone, intent, and key persuasive phrases

How "URL/HTML resource support" actually works with a local LLM:
    llama3.1:8b cannot browse the internet. It only understands plain text.
    This script acts as the bridge:
        1. urllib fetches the raw HTML
        2. html.parser strips tags, scripts, and boilerplate
        3. Clean plain text is sent to each agent
    The model's job is pure text intelligence — we handle the web part.

Usage:
    python web_agents.py <url>
    python web_agents.py https://ollama.com
    python web_agents.py https://www.python.org/about/
"""

import json
import re
import sys
import textwrap
import urllib.request
import urllib.error
from html.parser import HTMLParser
from typing import Any

from main import ConversationSession, DEFAULT_MODEL, OLLAMA_BASE_URL


# ── Global Config ──────────────────────────────────────────────────────────────

MAX_WORDS      = 3_000   # words sent to each agent (fits within 8k context)
MAX_RETRIES    = 2       # how many times to ask model to fix bad JSON
AGENT_MODEL    = DEFAULT_MODEL
AGENT_BASE_URL = OLLAMA_BASE_URL


# ── HTML → Plain Text ──────────────────────────────────────────────────────────

class _TextExtractor(HTMLParser):
    """
    Minimal HTML parser that strips markup and extracts visible text only.
    Entire content of <script>, <style>, <nav>, <footer> etc. is dropped.
    """
    _SKIP_TAGS = {
        "script", "style", "nav", "footer", "head",
        "noscript", "svg", "iframe", "aside",
    }

    def __init__(self):
        super().__init__()
        self._skip_depth = 0
        self._parts: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag in self._SKIP_TAGS:
            self._skip_depth += 1

    def handle_endtag(self, tag):
        if tag in self._SKIP_TAGS and self._skip_depth > 0:
            self._skip_depth -= 1

    def handle_data(self, data):
        if self._skip_depth == 0:
            stripped = data.strip()
            if stripped:
                self._parts.append(stripped)

    def get_text(self) -> str:
        return " ".join(self._parts)


class WebScraper:
    """
    Fetches a URL and returns (page_title, clean_plain_text).
    Pure stdlib — no external packages required.
    """
    _HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0 Safari/537.36"
        ),
        "Accept-Language": "en-US,en;q=0.9",
    }

    @classmethod
    def fetch(cls, url: str, max_words: int = MAX_WORDS) -> tuple[str, str]:
        """
        Download the page, strip HTML, and return (title, clean_text).
        Text is truncated to max_words to keep within the model's context window.
        """
        req = urllib.request.Request(url, headers=cls._HEADERS)
        with urllib.request.urlopen(req, timeout=20) as resp:
            charset = resp.headers.get_content_charset() or "utf-8"
            html = resp.read().decode(charset, errors="replace")

        # Extract page title from raw HTML
        title_m = re.search(r"<title[^>]*>(.*?)</title>", html, re.I | re.S)
        title = re.sub(r"<[^>]+>", "", title_m.group(1)).strip() if title_m else url

        # Strip HTML to plain text
        extractor = _TextExtractor()
        extractor.feed(html)
        raw_text = extractor.get_text()

        # Collapse runs of whitespace
        clean = re.sub(r"\s{2,}", " ", raw_text).strip()

        # Truncate to respect the model's 8k context window
        words = clean.split()
        if len(words) > max_words:
            clean = " ".join(words[:max_words]) + "\n[... page truncated to fit context window ...]"

        return title, clean


# ── JSON Extraction Utility ────────────────────────────────────────────────────

def _extract_json(text: str) -> Any:
    """
    Robustly parse JSON from a model response.
    Handles: raw JSON, ```json...```, ``` ... ```, or JSON buried in prose.
    """
    text = text.strip()

    # 1. Direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 2. Strip markdown code fences
    m = re.search(r"```(?:json)?\s*([\s\S]+?)\s*```", text)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass

    # 3. Find the outermost { ... } block
    m = re.search(r"\{[\s\S]+\}", text)
    if m:
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            pass

    raise ValueError(f"No valid JSON found in model response:\n{text[:400]}")


# ── Base Agent ─────────────────────────────────────────────────────────────────

class BaseAgent:
    """
    Wraps a ConversationSession with a specialised system prompt.
    Subclasses implement SYSTEM_PROMPT and _build_prompt().
    """
    NAME: str = "Agent"
    SYSTEM_PROMPT: str = ""

    def __init__(self):
        self._session = ConversationSession(
            model=AGENT_MODEL,
            base_url=AGENT_BASE_URL,
            system_prompt=self.SYSTEM_PROMPT,
        )

    def analyse(self, text: str) -> dict:
        """
        Run this agent on the provided text.
        Retries up to MAX_RETRIES times if the model returns malformed JSON.
        Returns a dict — either the parsed result or an {"error": ...} fallback.
        """
        prompt = self._build_prompt(text)

        for attempt in range(1, MAX_RETRIES + 2):
            self._session.reset()               # fresh context per attempt
            raw = self._session.chat(prompt)
            try:
                return _extract_json(raw)
            except ValueError:
                if attempt <= MAX_RETRIES:
                    # Give the model a chance to self-correct
                    raw = self._session.chat(
                        "Your previous response was not valid JSON. "
                        "Please respond with ONLY the JSON object — "
                        "no markdown, no explanations, nothing else."
                    )
                    try:
                        return _extract_json(raw)
                    except ValueError:
                        continue

        return {"error": "Model did not return valid JSON after retries", "raw": raw[:300]}

    def _build_prompt(self, text: str) -> str:  # pragma: no cover
        raise NotImplementedError


# ── Agent 1: Page Classifier ───────────────────────────────────────────────────

class PageClassifierAgent(BaseAgent):
    """
    Classifies what type of webpage the content belongs to.
    Output categories: home | about-us | careers | products |
                       services | partners | blog | contact | other
    """
    NAME = "Page Classification"
    SYSTEM_PROMPT = """You are an expert web content categoriser.
You will receive plain text scraped from a webpage.
Your ONLY job is to classify what type of page it is.

Valid page types: home, about-us, careers, products, services, partners, blog, contact, other

You MUST respond with ONLY this JSON object and absolutely nothing else:
{
  "page_type": "<one of the valid types above>",
  "confidence": "<high|medium|low>",
  "reasoning": "<one concise sentence explaining your classification>"
}"""

    def _build_prompt(self, text: str) -> str:
        return (
            "Classify the following webpage content.\n"
            "Respond with ONLY the JSON object.\n\n"
            f"PAGE CONTENT:\n{text}"
        )


# ── Agent 2: Named Entity Recognition ─────────────────────────────────────────

class NERAgent(BaseAgent):
    """
    Extracts named entities from webpage text:
    people, organizations, locations, products, technologies.
    """
    NAME = "Named Entity Recognition"
    SYSTEM_PROMPT = """You are a Named Entity Recognition (NER) expert.
You will receive plain text scraped from a webpage.
Extract all named entities and group them by category.

You MUST respond with ONLY this JSON object and absolutely nothing else:
{
  "people": ["full names of individuals mentioned"],
  "organizations": ["company, institution, or organisation names"],
  "locations": ["cities, countries, regions, addresses"],
  "products": ["specific product or service names"],
  "technologies": ["software, platforms, tools, programming languages, frameworks"]
}

Rules:
- Use empty lists [] if a category has no entities
- Do not include generic words, only proper named entities
- Deduplicate: each entity appears once"""

    def _build_prompt(self, text: str) -> str:
        return (
            "Extract all named entities from the following webpage content.\n"
            "Respond with ONLY the JSON object.\n\n"
            f"PAGE CONTENT:\n{text}"
        )


# ── Agent 3: Topic Modeling ────────────────────────────────────────────────────

class TopicModelingAgent(BaseAgent):
    """
    Identifies the main topics, themes, and keywords from webpage text.
    """
    NAME = "Topic Modeling"
    SYSTEM_PROMPT = """You are a topic modelling and content analysis expert.
You will receive plain text scraped from a webpage.
Identify the primary topic, secondary themes, important keywords, and write a one-sentence summary.

You MUST respond with ONLY this JSON object and absolutely nothing else:
{
  "primary_topic": "the single most important topic or theme",
  "secondary_topics": ["up to 4 supporting topics or subtopics"],
  "keywords": ["up to 8 significant keywords or key phrases"],
  "one_line_summary": "A single informative sentence summarising what this page is about."
}

Rules:
- primary_topic should be a short noun phrase (2–5 words)
- secondary_topics should be distinct from each other
- keywords should reflect the actual vocabulary used on the page"""

    def _build_prompt(self, text: str) -> str:
        return (
            "Identify the topics and themes in the following webpage content.\n"
            "Respond with ONLY the JSON object.\n\n"
            f"PAGE CONTENT:\n{text}"
        )


# ── Agent 4: Sentiment Analysis ────────────────────────────────────────────────

class SentimentAnalysisAgent(BaseAgent):
    """
    Analyses the tone, sentiment, and communicative intent of webpage text.
    """
    NAME = "Sentiment Analysis"
    SYSTEM_PROMPT = """You are a sentiment analysis and tone detection expert.
You will receive plain text scraped from a webpage.
Analyse the overall sentiment, emotional tone, communicative intent, and notable persuasive phrases.

You MUST respond with ONLY this JSON object and absolutely nothing else:
{
  "overall_sentiment": "<positive|neutral|negative>",
  "confidence": "<high|medium|low>",
  "tone": ["descriptors such as professional, casual, persuasive, formal, enthusiastic, technical"],
  "intent": "the primary communicative intent e.g. lead generation, brand building, informational, recruiting",
  "key_phrases": ["up to 5 notable phrases that best reflect the tone or intent of the page"]
}"""

    def _build_prompt(self, text: str) -> str:
        return (
            "Analyse the sentiment and tone of the following webpage content.\n"
            "Respond with ONLY the JSON object.\n\n"
            f"PAGE CONTENT:\n{text}"
        )


# ── Orchestrator ───────────────────────────────────────────────────────────────

class WebAnalysisOrchestrator:
    """
    Coordinates all four agents against a single URL.
    Fetches the page once, runs each agent sequentially, and returns
    a unified result dict.
    """

    def __init__(self):
        self._agents: list[BaseAgent] = [
            PageClassifierAgent(),
            NERAgent(),
            TopicModelingAgent(),
            SentimentAnalysisAgent(),
        ]

    def analyse(self, url: str) -> dict:
        """
        Full analysis pipeline for a URL.
        Returns a dict with keys: url, title, word_count, analysis.
        """
        # ── Step 1: Fetch ──────────────────────────────────────────────────────
        print(f"\n  Fetching  : {url}")
        try:
            title, text = WebScraper.fetch(url)
        except urllib.error.URLError as e:
            print(f"  [ERROR] Could not fetch URL: {e}")
            sys.exit(1)

        word_count = len(text.split())
        print(f"  Title     : {title}")
        print(f"  Words     : {word_count:,} (sent to each agent)")
        print()

        # ── Step 2: Run agents ─────────────────────────────────────────────────
        results: dict[str, dict] = {}
        for i, agent in enumerate(self._agents, 1):
            label = agent.NAME
            print(f"  [{i}/4] {label:<30}", end="", flush=True)
            results[label] = agent.analyse(text)
            status = "⚠  (parse error)" if "error" in results[label] else "✓"
            print(status)

        return {
            "url": url,
            "title": title,
            "word_count": word_count,
            "analysis": results,
        }


# ── Pretty Printer ─────────────────────────────────────────────────────────────

_W = 64   # report width

def _hr(char="─"):
    print(char * (_W + 2))

def _section(label: str):
    print(f"\n\033[1m{label}\033[0m")   # bold on most terminals

def _row(key: str, value: str, key_width: int = 16):
    key_str = (key + " ").ljust(key_width)
    wrapped = textwrap.fill(
        value,
        width=_W - key_width - 2,
        subsequent_indent=" " * (key_width + 4),
    )
    print(f"  {key_str}: {wrapped}")

def _print_report(data: dict):
    url        = data["url"]
    title      = data["title"]
    word_count = data["word_count"]
    analysis   = data["analysis"]

    print()
    print("╔" + "═" * _W + "╗")
    print("║" + "  Web Analysis Report".center(_W) + "║")
    print("╠" + "═" * _W + "╣")
    print(f"║  URL   : {url[: _W - 10]:<{_W - 10}}  ║")
    print(f"║  Title : {title[:_W - 10]:<{_W - 10}}  ║")
    print(f"║  Words : {str(word_count):<{_W - 10}}  ║")
    print("╚" + "═" * _W + "╝")

    # ── 1. Page Classification ─────────────────────────────────────────────────
    _section("[1/4] Page Classification")
    clf = analysis.get("Page Classification", {})
    if "error" not in clf:
        _row("Type",       clf.get("page_type", "?").upper())
        _row("Confidence", clf.get("confidence", "?"))
        _row("Reasoning",  clf.get("reasoning",  "?"))
    else:
        print(f"  ⚠  {clf['error']}")
        if "raw" in clf:
            print(f"     Raw: {clf['raw']}")

    # ── 2. Named Entities ─────────────────────────────────────────────────────
    _section("[2/4] Named Entities")
    ner = analysis.get("Named Entity Recognition", {})
    if "error" not in ner:
        for field, label in [
            ("people",        "People"),
            ("organizations", "Organizations"),
            ("locations",     "Locations"),
            ("products",      "Products"),
            ("technologies",  "Technologies"),
        ]:
            items = ner.get(field, [])
            if items:
                _row(label, ", ".join(str(i) for i in items[:10]))
    else:
        print(f"  ⚠  {ner['error']}")

    # ── 3. Topic Modeling ─────────────────────────────────────────────────────
    _section("[3/4] Topic Modeling")
    top = analysis.get("Topic Modeling", {})
    if "error" not in top:
        _row("Primary Topic",  str(top.get("primary_topic", "?")))
        secondary = top.get("secondary_topics", [])
        if secondary:
            _row("Other Topics", ", ".join(secondary))
        keywords = top.get("keywords", [])
        if keywords:
            _row("Keywords", ", ".join(keywords))
        summary = top.get("one_line_summary", "")
        if summary:
            _row("Summary", summary)
    else:
        print(f"  ⚠  {top['error']}")

    # ── 4. Sentiment Analysis ─────────────────────────────────────────────────
    _section("[4/4] Sentiment Analysis")
    sent = analysis.get("Sentiment Analysis", {})
    if "error" not in sent:
        sentiment  = sent.get("overall_sentiment", "?").capitalize()
        confidence = sent.get("confidence", "?")
        _row("Sentiment", f"{sentiment}  (confidence: {confidence})")
        tone = sent.get("tone", [])
        if tone:
            _row("Tone", ", ".join(tone))
        _row("Intent", sent.get("intent", "?"))
        phrases = sent.get("key_phrases", [])
        if phrases:
            _row("Key Phrases", "  |  ".join(f'"{p}"' for p in phrases[:5]))
    else:
        print(f"  ⚠  {sent['error']}")

    print()
    _hr()


# ── CLI Entry Point ────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print("Usage:  python web_agents.py <url>")
        print("Example: python web_agents.py https://ollama.com")
        sys.exit(1)

    url = sys.argv[1]
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    print("=" * (_W + 2))
    print("  Ollama Multi-Agent Web Analyser".center(_W + 2))
    print(f"  Model: {AGENT_MODEL}".center(_W + 2))
    print("=" * (_W + 2))

    orchestrator = WebAnalysisOrchestrator()
    data = orchestrator.analyse(url)
    _print_report(data)

    # Optionally save raw JSON results
    out_file = "analysis_result.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"  Raw JSON saved to: {out_file}\n")


if __name__ == "__main__":
    main()
