"""
Agent: sentiment_analysis
--------------------------
Uses llama3.1:8b to analyse the overall sentiment, tone, and communicative
intent of webpage plain text.

Primary function: sentiment_analysis(text)
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from agents._base import llm_analyse

# ── Agent metadata ─────────────────────────────────────────────────────────────

DESCRIPTION = (
    "Analyses the sentiment, tone, and communicative intent of text using AI. "
    "Returns: overall_sentiment (positive/neutral/negative), confidence, "
    "tone (list of descriptors like professional/persuasive/casual), "
    "intent (e.g. lead generation, brand building, informational, recruiting), "
    "key_phrases (notable phrases that reflect the tone)."
)

PARAMETERS = {
    "text": {
        "type":        "string",
        "required":    True,
        "description": "Clean plain text to analyse for sentiment and tone",
    }
}

_SYSTEM_PROMPT = """You are a sentiment analysis and tone detection expert.
Given the plain text of a webpage, analyse its overall sentiment, emotional tone, communicative intent, and notable persuasive phrases.

You MUST respond with ONLY this JSON object and absolutely nothing else — no markdown, no explanation:
{
  "overall_sentiment": "<positive|neutral|negative>",
  "confidence":        "<high|medium|low>",
  "tone":              ["tone descriptors, e.g. professional, persuasive, enthusiastic, technical, casual, formal"],
  "intent":            "the primary communicative goal, e.g. lead generation, brand building, informational, recruiting",
  "key_phrases":       ["up to 5 notable phrases that best reflect the tone or intent of the page"]
}"""

# ── Primary function ───────────────────────────────────────────────────────────

def sentiment_analysis(text: str) -> dict:
    """
    Analyse sentiment, tone, and intent from plain text.

    Args:
        text: Clean plain text to analyse

    Returns:
        {
            "overall_sentiment": str,
            "confidence":        str,
            "tone":              list[str],
            "intent":            str,
            "key_phrases":       list[str],
        }
    """
    prompt = (
        "Analyse the sentiment and tone of the following text. "
        "Respond with ONLY the JSON object.\n\n"
        f"TEXT:\n{text}"
    )
    return llm_analyse(
        system_prompt=_SYSTEM_PROMPT,
        user_prompt=prompt,
        agent_name="sentiment_analysis",
    )
