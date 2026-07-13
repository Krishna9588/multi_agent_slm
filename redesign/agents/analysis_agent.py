import json
import re
from langchain_core.messages import SystemMessage, HumanMessage
from redesign.core.models import get_llm
from redesign.core.state import AgentState

def analysis_agent(state: AgentState) -> dict:
    """
    The Analysis Agent node.
    It takes the raw data gathered by the research agent and structures it into JSON based on the user's requirements.
    """
    print("--- [Analysis Agent] Starting Data Structuring ---")
    
    raw_data_summary = state.get("raw_data", {}).get("research_summary", "")
    task_prompt = state.get("task_prompt", "")
    
    if not raw_data_summary:
        print("Warning: No raw data found to analyze.")
        return {"structured_data": {"error": "No raw data provided by researcher."}}

    system_prompt = f"""You are an elite Data Analysis Agent.
Your job is to read the RAW DATA provided below, extract the precise fields requested in the USER PROMPT, and return a single valid JSON object.
CRITICAL RULES:
1. Output ONLY valid JSON. No markdown formatting, no conversational text before or after.
2. DO NOT hallucinate. If a requested field is not present in the RAW DATA, set its value to "Not Found".
3. Use exact keys based on the user's requested details.

USER PROMPT:
{task_prompt}
"""

    human_prompt = f"RAW DATA:\n{raw_data_summary}"
    
    llm = get_llm(temperature=0.0)
    result = llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=human_prompt)
    ])
    
    # Attempt to parse JSON from the LLM output (strip markdown blocks if any exist)
    output_text = result.content.strip()
    
    # regex to find json block
    match = re.search(r"```(?:json)?(.*?)```", output_text, re.DOTALL)
    if match:
        output_text = match.group(1).strip()
        
    try:
        structured_data = json.loads(output_text)
    except json.JSONDecodeError:
        print("Warning: Failed to parse JSON from LLM output. Using raw text.")
        structured_data = {"extracted_text": output_text, "error": "Invalid JSON format returned."}
        
    print("--- [Analysis Agent] Finished Data Structuring ---")
    
    return {
        "structured_data": structured_data,
        "messages": [result]
    }

def main():
    """Standalone test function for the analysis agent."""
    print("Testing Analysis Agent directly...")
    dummy_state = {
        "task_prompt": "Extract the Organization Name, Headquarters City, and Founder Name.",
        "raw_data": {
            "research_summary": "eChai Ventures is based in Pune. It was founded by Jatin Chaudhary."
        },
        "messages": [],
        "structured_data": {},
        "report_path": "",
        "errors": []
    }
    result = analysis_agent(dummy_state)
    print("\nResult:")
    print(json.dumps(result["structured_data"], indent=2))

if __name__ == "__main__":
    main()
