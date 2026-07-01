"""
Agent: ner_agent
-----------------
Uses llama3.1:8b to extract Named Entities from webpage plain text.
Entity types: people, organizations, locations, products, technologies.

Primary function: ner_agent(text)
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from agents._base import llm_analyse

# ── Agent metadata ─────────────────────────────────────────────────────────────

DESCRIPTION = (
    "Extracts named entities from text using AI. "
    "Entity types extracted: people (individual names with their designation/role), "
    "organizations (companies/institutions with context), "
    "locations (cities/countries/regions), products (specific product or service names), "
    "technologies (software/tools/platforms/frameworks). "
    "Returns a dict with each category as a list of detailed objects (dictionaries)."
)

PARAMETERS = {
    "text": {
        "type":        "string",
        "required":    True,
        "description": "Clean plain text to extract named entities from",
    }
}

_SYSTEM_PROMPT = """You are a Named Entity Recognition (NER) expert.
Given the plain text of a webpage, extract all named entities and group them by category.
Provide detailed information for each entity when available in the text.

You MUST respond with ONLY this JSON object and absolutely nothing else — no markdown, no explanation:
{
  "people":        [{"name": "full name of person", "designation": "their role, title, or designation if mentioned"}],
  "organizations": [{"name": "company or institution name", "context": "brief context on what they do or how they are mentioned"}],
  "locations":     [{"name": "city, country, region", "context": "how it relates to the text"}],
  "products":      [{"name": "product or service name", "description": "brief description if available"}],
  "technologies":  [{"name": "software, API, framework", "context": "how it is used in the text"}]
}

Rules:
- Use an empty list [] for categories with no entities.
- If multiple people or entities are found, add a new dictionary object to the list for each one.
- Include only proper named entities, not generic words.
- Deduplicate: each entity should appear only once per category.
- If designation, context, or description is not mentioned, use null or an empty string."""

# ── Primary function ───────────────────────────────────────────────────────────

def ner_agent(text: str) -> dict:
    """
    Extract named entities from plain text.

    Args:
        text: Clean plain text to analyse

    Returns:
        {
            "people":        list[dict],
            "organizations": list[dict],
            "locations":     list[dict],
            "products":      list[dict],
            "technologies":  list[dict],
        }
    """
    prompt = (
        "Extract all named entities from the following text. "
        "Respond with ONLY the JSON object.\n\n"
        f"TEXT:\n{text}"
    )
    return llm_analyse(
        system_prompt=_SYSTEM_PROMPT,
        user_prompt=prompt,
        agent_name="ner_agent",
    )
