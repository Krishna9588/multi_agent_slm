"""
Agent: qa_agent
---------------
The Quality Assurance (Critic) Agent.
Evaluates data and output from other agents against the user's original requirements.
If hallucinations or missing fields are detected, it rejects the work and provides feedback.
"""

import json
from core.models import get_conversation_session

DESCRIPTION = (
    "A Quality Assurance (Critic) Agent. "
    "Pass it the original user requirement and the generated output (e.g., a JSON string, a scraped dataset). "
    "It will evaluate the output and return either a 'PASS' or a 'FAIL' with detailed feedback on what needs to be fixed. "
    "Always use this before finalizing complex data extraction to ensure accuracy."
)

PARAMETERS = {
    "original_requirement": {
        "type": "string",
        "required": True,
        "description": "What the user originally asked for (e.g., 'Extract name and email as JSON').",
    },
    "generated_output": {
        "type": "string",
        "required": True,
        "description": "The data or text produced by the working agent that needs to be reviewed.",
    }
}

def qa_agent(original_requirement: str, generated_output: str) -> dict:
    """Evaluates the output against the requirement using an LLM critic."""
    
    system_prompt = (
        "You are an elite Quality Assurance AI. Your job is to rigorously evaluate generated output against the original requirement.\n"
        "Look for:\n"
        "1. Hallucinations (made up data)\n"
        "2. Missing required fields\n"
        "3. Incorrect formatting (e.g. invalid JSON when JSON was requested)\n\n"
        "Output ONLY a valid JSON object in this format:\n"
        "{\n"
        "  \"status\": \"PASS\" | \"FAIL\",\n"
        "  \"feedback\": \"Detailed explanation of what is wrong and how to fix it. If PASS, say 'Output looks good.'\"\n"
        "}"
    )
    
    prompt = f"Original Requirement:\n{original_requirement}\n\nGenerated Output:\n{generated_output}"
    
    try:
        session = get_conversation_session(system_prompt=system_prompt)
        response = session.chat(prompt, format="json")
        
        # Clean markdown if present
        if response.startswith("```"):
            import re
            m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", response, re.DOTALL)
            if m:
                response = m.group(1)
                
        result = json.loads(response)
        return {
            "qa_status": result.get("status", "FAIL"),
            "feedback": result.get("feedback", "No feedback provided.")
        }
    except Exception as e:
        return {"error": f"QA Evaluation failed: {str(e)}"}
