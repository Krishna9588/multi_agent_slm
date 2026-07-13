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
        "required":    False,
        "description": "Clean plain text to extract named entities from. (Not required if source_file is provided).",
    },
    "source_file": {
        "type":        "string",
        "required":    False,
        "description": "Absolute filepath to a JSON file containing the data. Use this when the text was saved to a memory file.",
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

def ner_agent(text: str = "", source_file: str = "") -> dict:
    import json
    # 1. Resolve input text
    if source_file:
        if not os.path.exists(source_file):
            return {"error": f"source_file not found: {source_file}"}
        try:
            with open(source_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict) and "text" in data:
                    text = data["text"]
                else:
                    text = str(data)
        except Exception as e:
            return {"error": f"Failed to load source_file: {e}"}
            
    if not text:
        return {"error": "You must provide either 'text' or a valid 'source_file'."}

    # 2. Chunking logic (max ~4000 chars per chunk to avoid context limit)
    CHUNK_SIZE = 4000
    chunks = [text[i:i+CHUNK_SIZE] for i in range(0, len(text), CHUNK_SIZE)]
    
    merged_results = {
        "people": [],
        "organizations": [],
        "locations": [],
        "products": [],
        "technologies": []
    }
    
    # 3. Process each chunk
    for idx, chunk in enumerate(chunks):
        if not chunk.strip(): continue
        prompt = (
            f"Extract all named entities from the following text (Chunk {idx+1}/{len(chunks)}). "
            "Respond with ONLY the JSON object.\n\n"
            f"TEXT:\n{chunk}"
        )
        chunk_result = llm_analyse(
            system_prompt=_SYSTEM_PROMPT,
            user_prompt=prompt,
            agent_name="ner_agent",
        )
        
        # Merge lists if it's a valid result dict
        if isinstance(chunk_result, dict) and "error" not in chunk_result:
            for key in merged_results.keys():
                items = chunk_result.get(key, [])
                if isinstance(items, list):
                    # Basic deduplication by dict contents
                    for item in items:
                        if item not in merged_results[key]:
                            merged_results[key].append(item)
                            
    return merged_results
