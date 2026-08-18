"""
LangChain / LangGraph Orchestrator
-----------------------------------
Replaces our custom orchestrator.py ReAct loop with a robust, memory-backed
LangGraph ReAct agent implementation.

Features:
- Full tracing via LangSmith (if enabled in .env)
- Uses primary model for reasoning and tool execution
- In-memory persistence across single process lifecycle
"""

import sys
import os
from typing import List

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import InMemorySaver
from langsmith import traceable

from core.models import get_lc_model, DEFAULT_MODEL
from core.lc_tools import ALL_TOOLS


# Global memory store for this session
_memory = InMemorySaver()

SYSTEM_PROMPT = """You are a powerful multi-agent AI system with access to specialized tools.
Always use multiple tools when needed to thoroughly complete the user's task.
Never guess when you can search.

Common workflows:
- Research tasks: search_agent -> web_scraper -> analyze (topic/ner) -> data_exporter_agent
- Analysis tasks: web_scraper -> ner_agent -> sentiment_analysis -> topic_modeling -> page_classifier

Available tools are clearly described in your tool signatures.
If the user asks for CSV, Excel, PDF, or DOCX output, you MUST use data_exporter_agent.
If you need to extract links from a page, use link_extractor.
If you need to run Python code, use code_executor_agent."""


def _smart_tool_select(task: str) -> List[callable]:
    """
    Returns the list of active tools.
    """
    return ALL_TOOLS


@traceable(name="LangChain Orchestrator")
def run_lc_agent(task: str, thread_id: str = "default_session") -> str:
    """
    Runs the LangGraph ReAct agent on the user's task.
    """
    tools_to_use = _smart_tool_select(task)

    try:
        model = get_lc_model("default")
        agent = create_react_agent(
            model=model,
            tools=tools_to_use,
            checkpointer=_memory,
            prompt=SYSTEM_PROMPT,
        )

        thread_config = {"configurable": {"thread_id": thread_id}}

        response = agent.invoke(
            {"messages": [{"role": "user", "content": task}]},
            thread_config
        )
        messages = response.get("messages", [])
        if messages:
            last_msg = messages[-1]
            return getattr(last_msg, "content", str(last_msg))
        return "Agent finished without output."
    except Exception as e:
        return f"Agent encountered an error during execution: {str(e)}"

