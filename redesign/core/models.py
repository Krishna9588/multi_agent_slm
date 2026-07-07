from langchain_ollama import ChatOllama

# We lock this purely to the local Ollama instance running on default port 11434
OLLAMA_BASE_URL = "http://localhost:11434"

def get_llm(model_name: str = "llama3.1:8b", temperature: float = 0.0):
    """
    Returns a configured local Ollama LLM instance for the agents.
    Default model is set to llama3.1:8b (or whichever you have pulled).
    """
    return ChatOllama(
        model=model_name,
        base_url=OLLAMA_BASE_URL,
        temperature=temperature
    )
