from redesign.core.state import AgentState
from redesign.core.models import get_llm
from redesign.core.tools import local_web_scraper, local_browser_agent

def researcher_node(state: AgentState):
    """
    The Researcher Agent.
    Responsible for using local web scraping and Playwright tools to gather context.
    """
    print("🤖 [Researcher Agent] Activating...")
    
    llm = get_llm().bind_tools([local_web_scraper, local_browser_agent])
    
    # Read the latest message from the user
    messages = state.get("messages", [])
    
    # TODO: Actually invoke the LLM with the tools and append the result
    # response = llm.invoke(messages)
    
    return {
        "current_phase": "researching",
        "context": state.get("context", "") + "\n[Data Gathered]"
    }
