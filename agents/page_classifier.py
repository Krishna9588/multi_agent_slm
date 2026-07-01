"""
Agent: page_classifier
------------------------
Uses llama3.1:8b to classify what type of webpage a given text belongs to.
Categories: home | about-us | careers | products | services | partners | blog | contact | other

Primary function: page_classifier(text)
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


from agents._base import extract_json, llm_analyse

# ── Agent metadata ─────────────────────────────────────────────────────────────

DESCRIPTION = (
    "Classifies the type of a webpage based on its text content. "
    "Valid categories: home, about-us, careers, products, services, partners, blog, contact, other. "
    "Returns: page_type, confidence (high/medium/low), reasoning."
)

PARAMETERS = {
    "text": {
        "type":        "string",
        "required":    True,
        "description": "Clean plain text content of the webpage to classify",
    }
}

_SYSTEM_PROMPT = """You are an expert web content categoriser.
Given the plain text of a webpage, classify what type of page it is.

Valid page types: home, about-us, careers, products, services, partners, blog, contact, other

You MUST respond with ONLY this JSON object and absolutely nothing else — no markdown, no explanation:
{
  "page_type": "<one of the valid types>",
  "confidence": "<high|medium|low>",
  "reasoning": "<one concise sentence explaining your classification>"
}"""

# ── Primary function ───────────────────────────────────────────────────────────

def page_classifier(text: str) -> dict:
    """
    Classify the webpage type from its plain-text content.

    Args:
        text: Clean plain text of the webpage

    Returns:
        {"page_type": str, "confidence": str, "reasoning": str}
    """
    prompt = (
        "Classify the following webpage content. "
        "Respond with ONLY the JSON object.\n\n"
        f"PAGE CONTENT:\n{text}"
    )
    return llm_analyse(
        system_prompt=_SYSTEM_PROMPT,
        user_prompt=prompt,
        agent_name="page_classifier",
    )
