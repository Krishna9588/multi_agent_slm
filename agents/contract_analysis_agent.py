"""
Agent: contract_analysis_agent
------------------------------
A Legal & Compliance Agent. Analyzes NDAs and MSAs to extract liabilities and breach terms.
"""

import os
import json
from core.models import get_conversation_session

DESCRIPTION = (
    "The Legal Paralegal Agent. Use this to analyze contracts, NDAs, and MSAs. "
    "It reads a document and extracts critical legal clauses such as liabilities, breach conditions, and non-competes."
)

PARAMETERS = {
    "file_path": {
        "type": "string",
        "description": "The absolute path to the text or markdown file containing the contract.",
        "required": True
    },
    "focus_areas": {
        "type": "array",
        "items": {"type": "string"},
        "description": "Optional list of specific legal areas to focus on (e.g., ['liabilities', 'indemnification']). Default is ['liabilities', 'breach terms', 'non-compete'].",
        "required": False
    }
}

def contract_analysis_agent(file_path: str, focus_areas: list[str] = None) -> dict:
    """Reads a contract and uses an LLM to perform deep legal extraction."""
    if not os.path.exists(file_path):
        return {"error": f"File not found: {file_path}"}
        
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            contract_text = f.read()
    except Exception as e:
        return {"error": f"Failed to read file: {str(e)}"}
        
    # Prevent massive files from blowing up the context window
    if len(contract_text) > 50000:
        contract_text = contract_text[:50000] + "\n\n... [CONTRACT TRUNCATED DUE TO LENGTH]"
        
    if not focus_areas:
        focus_areas = ["liabilities", "breach terms", "non-compete"]
        
    system_prompt = (
        "You are an expert corporate lawyer and paralegal. Your task is to analyze the provided contract "
        "and extract specific legal clauses exactly as they appear, along with a plain-english summary of their implications.\n"
        "You MUST output ONLY a valid JSON object matching this schema:\n"
        "{\n"
        "  \"contract_summary\": \"Brief overview\",\n"
        "  \"extracted_clauses\": [\n"
        "    {\"focus_area\": \"...\", \"exact_text\": \"...\", \"plain_english_implication\": \"...\"}\n"
        "  ]\n"
        "}\n"
        "Do not include markdown blocks or conversational text. Output pure JSON."
    )
    
    prompt = (
        f"Please analyze the following contract and focus on these areas: {', '.join(focus_areas)}.\n\n"
        f"--- CONTRACT TEXT ---\n"
        f"{contract_text}\n"
        f"---------------------\n"
    )
    
    try:
        session = get_conversation_session(system_prompt=system_prompt)
        response = session.chat(prompt, format="json")
        
        # Try to parse the JSON
        data = json.loads(response)
        return {"success": True, "analysis": data}
        
    except json.JSONDecodeError:
        return {"error": "LLM failed to output valid JSON for the contract analysis."}
    except Exception as e:
        return {"error": f"LLM processing failed: {str(e)}"}
