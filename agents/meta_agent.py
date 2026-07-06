"""
Agent: meta_agent
-----------------
The Tool Creator Agent.
Allows the orchestrator to dynamically write new agent scripts and save them to the agents/ folder.
Once saved, the orchestrator can reload its registry and immediately use the new tool.
"""

import os
import re

DESCRIPTION = (
    "Create a new agent tool by saving a complete Python script to the agents/ folder. "
    "Use this when you need a capability you don't currently have. "
    "The python_code MUST follow the agent file convention: "
    "1. Define a DESCRIPTION string. "
    "2. Define a PARAMETERS dict mapping argument names to type/required/description. "
    "3. Define a main function with the EXACT SAME NAME as the tool_name. "
    "4. The function must return a dict."
)

PARAMETERS = {
    "tool_name": {
        "type": "string",
        "required": True,
        "description": "The name of the new tool (e.g., 'apify_scraper'). Must be a valid python identifier.",
    },
    "python_code": {
        "type": "string",
        "required": True,
        "description": "The complete, valid Python code for the new agent.",
    }
}

def meta_agent(tool_name: str, python_code: str) -> dict:
    """Saves a new agent script to the agents directory."""
    
    # Clean the tool_name to ensure it's a valid filename
    tool_name = re.sub(r'[^a-zA-Z0-9_]', '', tool_name)
    if not tool_name:
        return {"error": "Invalid tool_name provided. Must contain alphanumeric characters."}
        
    filename = f"{tool_name}.py"
    
    # Get the directory of this file (which is the agents/ folder)
    agents_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(agents_dir, filename)
    
    # Check if we are overwriting a core agent
    protected_agents = ["_base.py", "__init__.py", "meta_agent.py", "code_executor_agent.py"]
    if filename in protected_agents:
        return {"error": f"Cannot overwrite protected system file: {filename}"}
        
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(python_code)
            
        return {
            "success": True,
            "message": f"Successfully created {filename} in the agents folder.",
            "file_path": file_path,
            "instruction": f"The orchestrator will automatically reload the registry. You can now use '{tool_name}' in your next step."
        }
    except Exception as e:
        return {"error": f"Failed to save {filename}: {str(e)}"}
