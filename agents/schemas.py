"""
Pillar 2: Pydantic Schemas for all agents.
-------------------------------------------
Defines strict output schemas for every text-analysis agent.
These schemas are used by _base.py (Instructor / fallback validator)
to guarantee the model returns well-structured, parseable JSON.

All agents import from this file — no schema duplication.
"""

from __future__ import annotations
from typing import Optional, List
from pydantic import BaseModel, Field


# ── NER Agent ─────────────────────────────────────────────────────────────────

class PersonEntity(BaseModel):
    name: str = Field(description="Full name of the person.")
    designation: Optional[str] = Field(None, description="Job title or role if mentioned.")

class OrganizationEntity(BaseModel):
    name: str = Field(description="Full name of the organization or company.")
    type: Optional[str] = Field(None, description="Type of organization, e.g. 'company', 'NGO', 'government'.")

class LocationEntity(BaseModel):
    name: str = Field(description="Name of the location, city, country, or region.")
    type: Optional[str] = Field(None, description="Type of location, e.g. 'city', 'country', 'region'.")

class DateEntity(BaseModel):
    value: str = Field(description="Date or time reference mentioned in text.")
    context: Optional[str] = Field(None, description="What the date refers to, if clear.")

class NEROutput(BaseModel):
    people: List[PersonEntity] = Field(default_factory=list, description="People mentioned in the text.")
    organizations: List[OrganizationEntity] = Field(default_factory=list, description="Organizations mentioned.")
    locations: List[LocationEntity] = Field(default_factory=list, description="Locations mentioned.")
    dates: List[DateEntity] = Field(default_factory=list, description="Dates and time references mentioned.")
    products: List[str] = Field(default_factory=list, description="Products, services, or technologies mentioned.")
    other: List[str] = Field(default_factory=list, description="Any other notable named entities not covered above.")


# ── Sentiment Analysis Agent ───────────────────────────────────────────────────

class SentimentOutput(BaseModel):
    overall_sentiment: str = Field(
        description="Overall sentiment: 'positive', 'negative', or 'neutral'."
    )
    confidence: float = Field(
        description="Confidence score from 0.0 (unsure) to 1.0 (certain)."
    )
    summary: str = Field(description="One or two sentence explanation of the sentiment.")
    key_phrases: List[str] = Field(
        default_factory=list,
        description="Key phrases from the text that drove the sentiment classification."
    )


# ── Page Classifier Agent ──────────────────────────────────────────────────────

class PageClassifierOutput(BaseModel):
    category: str = Field(
        description="Primary content category, e.g. 'blog', 'landing page', 'product page', 'news article', 'documentation', 'e-commerce', 'about page', 'contact page'."
    )
    sub_category: Optional[str] = Field(None, description="More specific sub-category if applicable.")
    confidence: float = Field(description="Confidence score from 0.0 to 1.0.")
    reasoning: str = Field(description="Short explanation for the classification.")
    language: str = Field(default="en", description="Detected primary language of the page (ISO 639-1 code).")


# ── Topic Modeling Agent ───────────────────────────────────────────────────────

class TopicOutput(BaseModel):
    main_topic: str = Field(description="The primary subject or theme of the content.")
    sub_topics: List[str] = Field(
        default_factory=list,
        description="Secondary themes or topics covered in the content."
    )
    keywords: List[str] = Field(
        default_factory=list,
        description="Most important keywords or phrases from the text."
    )
    summary: str = Field(description="A 2-3 sentence summary of the content's topics.")


# ── Search Agent Output ────────────────────────────────────────────────────────

class SearchResult(BaseModel):
    title: str = Field(description="Title of the search result.")
    url: str = Field(description="Full URL of the result.")
    snippet: str = Field(description="Short description or excerpt from the result.")
    source: str = Field(default="duckduckgo", description="Which search backend returned this result.")

class SearchOutput(BaseModel):
    query: str = Field(description="The original search query.")
    results: List[SearchResult] = Field(description="List of top search results.")
    total: int = Field(description="Total number of results returned.")
