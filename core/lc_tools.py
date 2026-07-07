"""
LangChain Tools Wrapper
-----------------------
Wraps all our native agents from `agents/` into LangChain @tool decorators
so they can be consumed natively by the LangChain orchestrator.
"""

from langchain.tools import tool
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

from agents.web_scraper import web_scraper as _web_scraper
from agents.search_agent import search_agent as _search_agent
from agents.sentiment_analysis import sentiment_analysis as _sentiment_analysis
from agents.ner_agent import ner_agent as _ner_agent
from agents.topic_modeling import topic_modeling as _topic_modeling
from agents.page_classifier import page_classifier as _page_classifier
from agents.link_extractor import link_extractor as _link_extractor
from agents.deep_research_agent import deep_research_agent as _deep_research_agent
from agents.data_exporter_agent import data_exporter_agent as _data_exporter_agent
from agents.meta_agent import meta_agent as _meta_agent
from agents.code_executor_agent import code_executor_agent as _code_executor_agent


@tool
def web_scraper(url: str, strategy: str = "auto", max_words: int = 3000) -> dict:
    """Fetches a URL and returns the clean plain-text content of the webpage.
    Uses a cascading strategy to handle static pages, bot-blocked sites, and JavaScript-heavy SPAs.
    Always call this first when you need to read or analyse a webpage."""
    return _web_scraper(url=url, strategy=strategy, max_words=max_words)


@tool
def search_agent(query: str, backend: str = "auto") -> dict:
    """Search the internet for real-time information or to find URLs related to a query.
    Returns the top results with title, URL, and snippet.
    Automatically routes to DuckDuckGo (general), Wikipedia (factual), or ArXiv (research).
    Use this when you need live data, don't know the exact URL, or need factual/research references."""
    return _search_agent(query=query, backend=backend)


@tool
def sentiment_analysis(text: str = "", source_file: str = "") -> dict:
    """Analyzes the sentiment, emotional tone, and subjectivity of text using AI.
    Returns a detailed breakdown of positive/negative sentiment, overall tone, and key emotional triggers.
    Provide either raw text or a source_file path."""
    return _sentiment_analysis(text=text, source_file=source_file)


@tool
def ner_agent(text: str = "", source_file: str = "") -> dict:
    """Extracts named entities from text using AI.
    Entity types extracted: people, organizations, locations, products, technologies.
    Provide either raw text or a source_file path."""
    return _ner_agent(text=text, source_file=source_file)


@tool
def topic_modeling(text: str = "", source_file: str = "") -> dict:
    """Analyzes text to extract the main themes, key topics, and high-level concepts using AI.
    Returns the primary theme, sub-topics, and a short summary abstract.
    Provide either raw text or a source_file path."""
    return _topic_modeling(text=text, source_file=source_file)


@tool
def page_classifier(text: str = "", source_file: str = "") -> dict:
    """Classifies a webpage or text document into a specific category/type using AI.
    Examples: 'news_article', 'ecommerce_product', 'blog_post', 'documentation', 'corporate_landing_page'.
    Provide either raw text or a source_file path."""
    return _page_classifier(text=text, source_file=source_file)


@tool
def link_extractor(url: str = "", html_content: str = "", base_url: str = "") -> dict:
    """Extracts, normalizes, and categorizes hyperlinks from a webpage.
    Provide either a URL to fetch, or raw html_content (with base_url for relative link resolution).
    Categorizes links into internal, external, and social."""
    return _link_extractor(url=url, html_content=html_content, base_url=base_url)


@tool
def deep_research_agent(query: str, depth: int = 2) -> dict:
    """Conducts autonomous, multi-step deep research on a topic.
    It automatically chains searches, reads pages, and follows links up to the specified depth.
    Use this for complex research queries that require aggregating information from multiple sources.
    Returns a comprehensive research report and citations."""
    return _deep_research_agent(query=query, depth=depth)


@tool
def data_exporter_agent(data: Any, format: str = "json", output_dir: str = "archive/outputs", filename: str = "export") -> dict:
    """Exports Python dictionaries/lists or strings into standard file formats.
    Supported formats: json, csv, md (markdown), txt, html.
    Use this to save the final results of your analysis to disk.
    Automatically handles formatting (e.g. flattening nested dicts for CSV)."""
    return _data_exporter_agent(data=data, format=format, output_dir=output_dir, filename=filename)


@tool
def meta_agent(task_description: str, target_agents: List[str] = None) -> dict:
    """A highly experimental agent that orchestrates other agents.
    Pass a complex sub-task and a list of target agents to use.
    It will attempt to run those agents to solve the sub-task."""
    if target_agents is None:
        target_agents = []
    return _meta_agent(task_description=task_description, target_agents=target_agents)


@tool
def code_executor_agent(code: str, language: str = "python", timeout: int = 10) -> dict:
    """Executes arbitrary code in an isolated environment (like a sandbox).
    Currently supports Python.
    Use this to run calculations, scripts, or test code snippets.
    Returns stdout, stderr, and execution status."""
    return _code_executor_agent(code=code, language=language, timeout=timeout)


ALL_TOOLS = [
    web_scraper,
    search_agent,
    sentiment_analysis,
    ner_agent,
    topic_modeling,
    page_classifier,
    link_extractor,
    deep_research_agent,
    data_exporter_agent,
    meta_agent,
    code_executor_agent
]
