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
    
    # Shared scratchpad for storing raw scraped data before processing
    context: str 
    
    # Track the current active phase (e.g., 'researching', 'coding', 'reporting')
    current_phase: str 
