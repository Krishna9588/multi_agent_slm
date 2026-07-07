"""
Agent: data_structuring_agent
-------------------------------
A self-correcting agent that dynamically infers the optimal JSON schema for unstructured text,
extracts the data, and validates it against hallucination/missing fields using the qa_agent.

Primary function: data_structuring_agent(text, context="web page")
"""

import json
import re
from core.models import get_conversation_session
from agents.qa_agent import qa_agent

DESCRIPTION = (
    "A self-correcting Data Structuring Agent. "
    "Use this tool to convert raw unstructured text (e.g. scraped markdown) into a highly structured JSON object. "
    "It automatically figures out the best column headers for the text, extracts the data, and internally uses a QA Critic "
    "to ensure zero hallucinations before returning the result."
)

PARAMETERS = {
    "text": {
        "type": "string",
        "required": True,
        "description": "The raw unstructured text or markdown to process."
    },
    "context": {
        "type": "string",
        "required": False,
        "description": "Context of what this text is (e.g. 'LinkedIn job posting', 'News article'). Helps the AI guess the schema."
    }
}

def _clean_json_output(response: str) -> dict:
    """Helper to extract JSON from LLM output even if it uses markdown blocks."""
    try:
        # First try direct parse
        return json.loads(response)
    except json.JSONDecodeError:
        # Try extracting from markdown block
        m = re.search(r"```(?:json)?\s*(\{.*\}|\[.*\])\s*```", response, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(1))
            except json.JSONDecodeError:
                pass
    return {}

def data_structuring_agent(text: str, context: str = "web page", max_retries: int = 3) -> dict:
    """
    Dynamically structures unstructured text using a schema discovery + QA loop.
    """
    
    # --- Step 1: Schema Discovery ---
    schema_prompt = (
        f"You are an expert data architect. Read this {context} and determine the optimal JSON schema (list of fields) "
        "that captures the most important structured data. For example, if it's a job post, fields might be "
        "['job_title', 'company', 'skills_required', 'experience_level', 'salary_range'].\n\n"
        "Return ONLY a JSON array of strings representing the column headers.\n\n"
        f"Text Snippet (first 1000 chars):\n{text[:1000]}"
    )
    
    try:
        schema_session = get_conversation_session(system_prompt="You only output valid JSON arrays of strings.")
        schema_resp = schema_session.chat(schema_prompt, format="json")
        schema = _clean_json_output(schema_resp)
        if not isinstance(schema, list) or len(schema) == 0:
            schema = ["title", "description", "entities"] # Fallback schema
    except Exception:
        schema = ["title", "description", "entities"]
        
    # --- Step 2: Extraction & QA Loop ---
    extract_system_prompt = (
        "You are an elite Data Extraction AI. Your job is to extract data strictly into the provided JSON schema. "
        "Do NOT hallucinate. If data is not present in the text, use null or an empty string. "
        "Output ONLY valid JSON matching the exact keys provided in the schema."
    )
    
    extract_session = get_conversation_session(system_prompt=extract_system_prompt)
    
    # Initial prompt
    current_prompt = f"Schema Keys required: {json.dumps(schema)}\n\nText to extract from:\n{text}"
    extracted_data = {}
    
    for attempt in range(max_retries):
        # 1. Extract
        try:
            extract_resp = extract_session.chat(current_prompt, format="json")
            extracted_data = _clean_json_output(extract_resp)
        except Exception as e:
            return {"error": f"Extraction failed: {str(e)}"}
            
        # If extraction completely failed to produce JSON
        if not extracted_data:
            current_prompt = f"Your last output was invalid JSON. Please strictly format as a JSON object with these keys: {schema}. Text:\n{text}"
            continue
            
        # 2. QA Validation
        original_req = f"Extract the following fields accurately without hallucinations: {schema}"
        qa_result = qa_agent(original_requirement=original_req, generated_output=json.dumps(extracted_data))
        
        status = qa_result.get("status", "FAIL")
        feedback = qa_result.get("feedback", "No feedback provided.")
        
        if status == "PASS":
            # Data is perfect!
            return {
                "status": "success",
                "schema": schema,
                "data": extracted_data,
                "retries_used": attempt
            }
        else:
            # Re-prompt with the critic's feedback
            current_prompt = (
                f"Your previous extraction failed QA. Critic Feedback:\n{feedback}\n\n"
                f"Please fix the errors and extract again. Output ONLY valid JSON."
            )
            
    # If we run out of retries, return the best effort but flag it
    return {
        "status": "partial_success",
        "warning": "Failed to pass QA within retry limit.",
        "schema": schema,
        "data": extracted_data
    }
