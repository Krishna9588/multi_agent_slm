def _autonomous_route(task: str) -> str:
    """Uses a fast local model to classify the user's intent into an execution mode."""
    prompt = f"""You are an Autonomous Router for an AI Agent ecosystem.
The user has provided a request: "{task}"

Analyze the request and choose ONE of the following modes:
- PREMIUM: For extremely complex tasks, massive deep research, multi-agent coordination, generating large reports (1000+ words).
- COUNCIL: For philosophical debate, code review, high-stakes decisions requiring multiple perspectives.
- AGENT: For standard tool execution, web scraping, API calls, simple data extraction.
- CHAT: For simple conversational queries, greetings, or questions that don't need any tools.

Respond with ONLY ONE WORD from the list above. No markdown, no explanations."""
    try:
        session = get_conversation_session(model="llama3.1:8b", system_prompt="You only output a single word: PREMIUM, COUNCIL, AGENT, or CHAT.")
        response = session.chat(prompt).strip().upper()
        if response in ["PREMIUM", "COUNCIL", "AGENT", "CHAT"]:
            return response
    except Exception:
        pass
    return "AGENT"  # Default fallback
