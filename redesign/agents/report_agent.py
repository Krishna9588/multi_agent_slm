import os
import json
from datetime import datetime
from langchain_core.messages import SystemMessage, HumanMessage
from redesign.core.models import get_llm
from redesign.core.state import AgentState

def report_agent(state: AgentState) -> dict:
    """
    The Report Agent node.
    It takes the structured JSON data and formats it into a highly polished, professional Markdown report.
    It also saves both the JSON and the MD file to the archive directory.
    """
    print("--- [Report Agent] Generating Final Report ---")
    
    structured_data = state.get("structured_data", {})
    
    if not structured_data:
        print("Warning: No structured data to report on.")
        return {"report_path": "Error: No data"}

    system_prompt = """You are an elite business report writer.
Your job is to take the structured JSON data provided and convert it into a beautiful, highly readable, professional Markdown report.
Use H1, H2, bullet points, and bold text to make it scannable and clean.
DO NOT hallucinate. Only include the information present in the JSON.
"""

    human_prompt = f"STRUCTURED JSON DATA:\n{json.dumps(structured_data, indent=2)}"
    
    llm = get_llm(temperature=0.3)
    result = llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=human_prompt)
    ])
    
    report_md = result.content.strip()
    
    # Save the output
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    org_name = structured_data.get("Organization Name", "Unknown_Organization").replace(" ", "_")
    
    outputs_dir = os.path.join(os.getcwd(), "archive", "outputs")
    os.makedirs(outputs_dir, exist_ok=True)
    
    md_path = os.path.join(outputs_dir, f"{org_name}_Report_{timestamp}.md")
    json_path = os.path.join(outputs_dir, f"{org_name}_Data_{timestamp}.json")
    
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(report_md)
        
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(structured_data, f, indent=2)
        
    print(f"--- [Report Agent] Report saved to {md_path} ---")
    
    return {
        "report_path": md_path,
        "messages": [result]
    }

def main():
    """Standalone test function for the report agent."""
    print("Testing Report Agent directly...")
    dummy_state = {
        "structured_data": {
            "Organization Name": "eChai Ventures Pune",
            "Entity Type": "Angel Network",
            "Founder": "Jatin Chaudhary",
            "Investment Stage": "Pre Seed"
        },
        "messages": [],
        "task_prompt": "",
        "raw_data": {},
        "report_path": "",
        "errors": []
    }
    result = report_agent(dummy_state)
    print("\nResult Path:", result["report_path"])
    
if __name__ == "__main__":
    main()
