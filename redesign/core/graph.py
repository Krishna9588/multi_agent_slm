from langgraph.graph import StateGraph, START, END
from redesign.core.state import AgentState
from redesign.agents.research_agent import research_agent
from redesign.agents.analysis_agent import analysis_agent
from redesign.agents.report_agent import report_agent

def create_graph():
    """
    Builds the Directed Acyclic Graph (DAG) for the LangGraph orchestrator.
    This defines the execution flow of the system.
    """
    workflow = StateGraph(AgentState)
    
    # 1. Add agent nodes to the graph
    workflow.add_node("researcher", research_agent)
    workflow.add_node("analyst", analysis_agent)
    workflow.add_node("reporter", report_agent)
    
    # 2. Define the routing edges
    workflow.add_edge(START, "researcher")
    workflow.add_edge("researcher", "analyst")
    workflow.add_edge("analyst", "reporter")
    workflow.add_edge("reporter", END)
    
    # 3. Compile the graph into an executable application
    return workflow.compile()
