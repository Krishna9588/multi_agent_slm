"""
agents/_base.py
----------------
Pillar 2: Shared utilities for all LLM-powered agents.

Provides:
    - extract_json(text)         : robustly pull JSON out of any model response.
    - validate_with_schema(data) : optional Pydantic schema validation.
    - llm_analyse(...)           : run a ConversationSession with JSON retry logic
                                   and optional Instructor-backed schema enforcement.

JSON enforcement hierarchy (most reliable → least reliable):
  1. Ollama's native `format="json"` injected at API level (active for all calls).
  2. Instructor library (if installed) for strict Pydantic model extraction.
  3. Regex-based JSON extraction from raw model output.
  4. Retry prompt asking the model to fix its own response.

This file is intentionally private (starts with _) so the auto-discovery
registry skips it.
"""

from __future__ import annotations

import json
import re
import sys
import os
from typing import Optional, Type

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from models import get_conversation_session, DEFAULT_MODEL

# How many times to ask the model to fix its JSON before giving up
_MAX_RETRIES = 3


# ── JSON Extraction ────────────────────────────────────────────────────────────

def extract_json(text: str):
    """
    Robustly parse JSON from a model response.

    Handles:
        - Raw JSON string
        - JSON wrapped in ```json ... ``` or ``` ... ```
        - JSON embedded somewhere inside prose
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

    # 3. Find the first complete { ... } block
    m = re.search(r"\{[\s\S]+\}", text)
    if m:
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            pass

    raise ValueError(f"No valid JSON found in:\n{text[:400]}")


# ── Pydantic Schema Validation ─────────────────────────────────────────────────

def validate_with_schema(data: dict, schema_class) -> dict:
    """
    Validate a parsed dict against a Pydantic schema.
    
    Args:
        data:         Parsed dict from model output.
        schema_class: A Pydantic BaseModel subclass (from agents/schemas.py).
        
    Returns:
        Validated and coerced dict, or the original dict if validation fails.
    """
    try:
        validated = schema_class(**data)
        return validated.model_dump()
    except Exception:
        # Don't crash on validation failure — return raw data
        return data


# ── Instructor-backed extraction (optional) ────────────────────────────────────

def _instructor_available() -> bool:
    try:
        import instructor  # noqa
        return True
    except ImportError:
        return False


# ── Main LLM Analysis Function ─────────────────────────────────────────────────

def llm_analyse(
    system_prompt: str,
    user_prompt: str,
    agent_name: str = "agent",
    model: str = DEFAULT_MODEL,
    schema_class: Optional[Type] = None,
) -> dict:
    """
    Run a ConversationSession with the given prompts and return parsed JSON.

    Enforcement pipeline:
      1. Ollama native `format="json"` (always active).
      2. Pydantic schema validation via `schema_class` if provided.
      3. Retry up to _MAX_RETRIES times on malformed output.
      4. On final failure: returns {\"error\": ..., \"raw\": ...}.

    Args:
        system_prompt: The agent's identity and output format instructions.
        user_prompt:   The actual task (text to analyse).
        agent_name:    Used in error messages.
        model:         Model name (Ollama or Gemini).
        schema_class:  Optional Pydantic BaseModel class to validate output against.

    Returns:
        Parsed dict from the model's JSON response, or an error dict.
    """
    session = get_conversation_session(
        model=model,
        system_prompt=system_prompt,
    )

    # Build a schema hint to embed in the user prompt if we have a schema
    schema_hint = ""
    if schema_class is not None:
        try:
            schema_hint = (
                f"\n\nYour response MUST conform to this JSON schema:\n"
                f"{json.dumps(schema_class.model_json_schema(), indent=2)}"
            )
        except Exception:
            pass

    raw = session.chat(user_prompt + schema_hint, format="json")

    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            parsed = extract_json(raw)
            # If schema provided, validate and coerce
            if schema_class is not None:
                parsed = validate_with_schema(parsed, schema_class)
            return parsed
        except ValueError:
            if attempt <= _MAX_RETRIES:
                retry_msg = (
                    "Your previous response was not valid JSON. "
                    "Please respond with ONLY the JSON object — "
                    "no markdown, no explanations, no extra text."
                )
                if schema_hint:
                    retry_msg += schema_hint
                raw = session.chat(retry_msg, format="json")
            else:
                break

    # Final fallback
    return {
        "error": f"{agent_name}: model did not return valid JSON after {_MAX_RETRIES} retries",
        "raw":   raw[:300],
    }
