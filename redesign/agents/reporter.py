from redesign.core.state import AgentState
from redesign.core.models import get_llm

def reporter_node(state: AgentState):
    """
    The Reporter Agent.
    Synthesizes the raw context and output into final structured 
    JSON/CSV files using local disk writes.
    """
    print("📝 [Reporter Agent] Activating...")
    
    llm = get_llm()
    
    # TODO: Read state["context"] and write to redesign/archive/outputs/
    
    return {
        "current_phase": "reporting"
    }
