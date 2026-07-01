"""
Agent: topic_modeling
----------------------
Uses llama3.1:8b to identify the main topics and themes in webpage plain text.

Primary function: topic_modeling(text)
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from agents._base import llm_analyse

# ── Agent metadata ─────────────────────────────────────────────────────────────

DESCRIPTION = (
    "Identifies the main topics, themes, and keywords in a piece of text using AI. "
    "Returns: primary_topic (the single most important theme), "
    "secondary_topics (up to 4 supporting themes), "
    "keywords (up to 8 significant terms), "
    "one_line_summary (a single sentence describing the page)."
)

PARAMETERS = {
    "text": {
        "type":        "string",
        "required":    True,
        "description": "Clean plain text to analyse for topics and themes",
    }
}

_SYSTEM_PROMPT = """You are a topic modelling and content analysis expert.
Given the plain text of a webpage, identify the primary topic, secondary themes, keywords, and write a one-sentence summary.

You MUST respond with ONLY this JSON object and absolutely nothing else — no markdown, no explanation:
{
  "primary_topic":    "the single most important topic or theme (2-5 words)",
  "secondary_topics": ["up to 4 supporting topics or subtopics"],
  "keywords":         ["up to 8 significant keywords or phrases from the text"],
  "one_line_summary": "A single informative sentence describing what this page is about."
}

Rules:
- primary_topic should be a concise noun phrase (not a full sentence)
- secondary_topics must be distinct from each other and from primary_topic
- keywords should reflect the actual vocabulary on the page"""

# ── Primary function ───────────────────────────────────────────────────────────

def topic_modeling(text: str) -> dict:
    """
    Identify topics and themes from plain text.

    Args:
        text: Clean plain text to analyse

    Returns:
        {
            "primary_topic":    str,
            "secondary_topics": list[str],
            "keywords":         list[str],
            "one_line_summary": str,
        }
    """
    prompt = (
        "Identify the topics and themes in the following text. "
        "Respond with ONLY the JSON object.\n\n"
        f"TEXT:\n{text}"
    )
    return llm_analyse(
        system_prompt=_SYSTEM_PROMPT,
        user_prompt=prompt,
        agent_name="topic_modeling",
    )
