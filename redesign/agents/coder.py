from redesign.core.state import AgentState
from redesign.core.models import get_llm
from redesign.core.tools import local_code_executor

def coder_node(state: AgentState):
    """
    The Coder Agent.
    Responsible for generating local code to solve tasks and passing it to 
    the local Docker executor tool.
    """
    print("💻 [Coder Agent] Activating...")
    
    llm = get_llm().bind_tools([local_code_executor])
    
    # TODO: Implement the reasoning and execution loop
    
    return {
        "current_phase": "coding"
    }
