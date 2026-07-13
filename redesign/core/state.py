from typing import TypedDict, Annotated, Sequence
from langchain_core.messages import BaseMessage
import operator

class AgentState(TypedDict):
    """
    The core state dictionary that is passed between nodes in the LangGraph.
    It holds conversation history, scraped context, and execution metadata.
    """
    # Messages list that appends new messages automatically
    messages: Annotated[Sequence[BaseMessage], operator.add]
    
    # Stores the raw research goal/prompt from the user
    task_prompt: str
    
    # Stores raw scraped texts from different sources (website, linkedin, etc.)
    raw_data: dict
    
    # Stores the synthesized JSON after the analysis agent runs
    structured_data: dict
    
    # Tracks the final report path
    report_path: str
    
    # Tracks any errors encountered in the graph
    errors: list[str] 
