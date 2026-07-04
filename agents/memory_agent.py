"""
Agent: memory_agent
-------------------
Manages long-term Vector DB storage.
Allows agents to actively store massive datasets, user preferences, or recall past interactions.
"""

from memory import save_session, recall_similar

DESCRIPTION = (
    "A Long-Term Memory Agent powered by a Vector Database. "
    "Use this agent to store important facts, massive scraped datasets, or user preferences that need to persist across sessions. "
    "You can also use this to query past memories."
)

PARAMETERS = {
    "action": {
        "type": "string",
        "required": True,
        "description": "Must be either 'store' or 'recall'.",
    },
    "query_or_data": {
        "type": "string",
        "required": True,
        "description": "If action='store', the data to remember. If action='recall', the search query.",
    },
    "tags": {
        "type": "string",
        "required": False,
        "description": "Optional comma-separated tags to associate with the memory when storing.",
    }
}

def memory_agent(action: str, query_or_data: str, tags: str = "") -> dict:
    """Stores or recalls information from the Vector DB."""
    action = action.lower().strip()
    if action == "save":
        action = "store"
    if action == "retrieve":
        action = "recall"
    
    if action == "store":
        try:
            # We use the existing save_session backend but customize it for arbitrary facts
            # The memory backend uses (task, answer, urls)
            save_session(task=f"Manual Storage: {tags}", answer=query_or_data, urls=[])
            return {"success": True, "message": "Successfully stored in long-term memory."}
        except Exception as e:
            return {"error": f"Failed to store memory: {str(e)}"}
            
    elif action == "recall":
        try:
            results = recall_similar(query_or_data, top_k=3)
            if not results:
                return {"success": True, "results": "No relevant memories found."}
                
            formatted = []
            for r in results:
                formatted.append(f"Match (Score {r.get('score', 0)}): {r.get('answer', '')}")
                
            return {"success": True, "results": "\n---\n".join(formatted)}
        except Exception as e:
            return {"error": f"Failed to recall memory: {str(e)}"}
            
    else:
        return {"error": "Invalid action. Must be 'store' or 'recall'."}
