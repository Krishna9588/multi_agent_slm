"""
Agent: setup_guide_agent
------------------------
The Onboarding Helper Agent.
It reads the documentation rulebook for a specific agent and generates a user-friendly,
conversational guide on how to fix setup/configuration issues.
"""

import os
from core.models import get_conversation_session

DESCRIPTION = (
    "The Onboarding Helper Agent. Use this agent whenever another agent fails due to missing API keys, "
    "missing accounts, or configuration issues. It provides the user with friendly, step-by-step setup instructions."
)

PARAMETERS = {
    "failing_agent_name": {
        "type": "string",
        "required": True,
        "description": "The name of the agent that failed (e.g., 'github_agent', 'search_agent').",
    },
    "error_message": {
        "type": "string",
        "required": False,
        "description": "The specific error message that was thrown, so the guide can be tailored to the exact issue.",
    }
}

def setup_guide_agent(failing_agent_name: str, error_message: str = "") -> dict:
    """Reads the docs for the failing agent and returns a friendly onboarding guide."""
    
    # Strip .py if accidentally passed
    if failing_agent_name.endswith(".py"):
        failing_agent_name = failing_agent_name[:-3]
        
    docs_path = os.path.join(os.getcwd(), "docs", "agents", f"{failing_agent_name}.md")
    
    if not os.path.exists(docs_path):
        return {
            "error": f"No documentation found for {failing_agent_name}.",
            "message": f"Please inform the user that the {failing_agent_name} lacks a rulebook in docs/agents/."
        }
        
    try:
        with open(docs_path, "r", encoding="utf-8") as f:
            docs_content = f.read()
    except Exception as e:
        return {"error": f"Failed to read documentation: {str(e)}"}
        
    system_prompt = (
        "You are an incredibly helpful and friendly Onboarding Assistant. "
        "Your job is to read the official technical documentation for an agent and translate it into a "
        "conversational, easy-to-follow step-by-step guide for a user who just encountered an error. "
        "Do not just paste the markdown. Speak directly to the user (e.g., 'It looks like you need to set up X! Here is how...')."
    )
    
    prompt = (
        f"The user tried to use '{failing_agent_name}' but encountered this error:\n"
        f"'{error_message}'\n\n"
        f"Here is the official documentation rulebook for '{failing_agent_name}':\n"
        f"---\n{docs_content}\n---\n\n"
        f"Please provide a friendly message guiding the user through the exact steps to fix their issue."
    )
    
    try:
        session = get_conversation_session(system_prompt=system_prompt)
        response = session.chat(prompt)
        return {
            "success": True,
            "agent": failing_agent_name,
            "guide": response.strip()
        }
    except Exception as e:
        return {"error": f"Failed to generate guide via LLM: {str(e)}"}
