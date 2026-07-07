from langgraph.graph import StateGraph, START, END
from redesign.core.state import AgentState
from redesign.agents.researcher import researcher_node
from redesign.agents.coder import coder_node
from redesign.agents.reporter import reporter_node

def create_graph():
    """
    Builds the Directed Acyclic Graph (DAG) for the LangGraph orchestrator.
    This defines the execution flow of the system.
    """
    workflow = StateGraph(AgentState)
    
    # 1. Add agent nodes to the graph
    workflow.add_node("researcher", researcher_node)
    workflow.add_node("coder", coder_node)
    workflow.add_node("reporter", reporter_node)
    
    # 2. Define the routing edges
    workflow.add_edge(START, "researcher")
    workflow.add_edge("researcher", "coder")
    workflow.add_edge("coder", "reporter")
    workflow.add_edge("reporter", END)
    
    # 3. Compile the graph into an executable application
    return workflow.compile()
