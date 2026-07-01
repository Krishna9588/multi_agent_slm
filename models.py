"""
Model Connectors
-----------------
Provides a unified ConversationSession interface for both Ollama and Gemini models.
Maintains conversation history for the session so the orchestrator and agents
don't need to manually manage context.

Supported models:
- llama3.1:8b (Ollama)
- llama3:8b (Ollama)
- qwen3:4b (Ollama)
- gemini-2.5-flash (Gemini via google-genai)
"""

import json
import os
import urllib.request
import urllib.error
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file (for GEMINI_API_KEY)
load_dotenv()

# ── Configuration ──────────────────────────────────────────────────────────────

OLLAMA_BASE_URL = "http://localhost:11434"
DEFAULT_MODEL   = "llama3.1:8b"

# List of known Ollama models
OLLAMA_MODELS = [
    "llama3.1:8b",
    "llama3:8b",
    "qwen3:4b",
    "granite4.1:3b",
    "phi4-mini:3.8b",
    "gemma:7b",
]

# List of known Gemini models
GEMINI_MODELS = [
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
]

# ── Base Interface ─────────────────────────────────────────────────────────────

class BaseConversationSession:
    """Base interface for all conversational models."""
    def __init__(self, model: str, system_prompt: Optional[str] = None):
        self.model = model
        self.system_prompt = system_prompt

    def chat(self, user_message: str, *, stream: bool = False, format: Optional[str] = None) -> str:
        raise NotImplementedError

    def reset(self):
        raise NotImplementedError

# ── Ollama Connector ───────────────────────────────────────────────────────────

class OllamaSession(BaseConversationSession):
    """Conversational session using local Ollama models."""
    
    def __init__(self, model: str, system_prompt: Optional[str] = None, base_url: str = OLLAMA_BASE_URL):
        super().__init__(model, system_prompt)
        self.base_url = base_url
        self._messages: list[dict] = []
        self.reset()

    def reset(self):
        self._messages.clear()
        if self.system_prompt:
            self._messages.append({
                "role": "system",
                "content": self.system_prompt,
            })

    def chat(self, user_message: str, *, stream: bool = False, format: Optional[str] = None) -> str:
        self._messages.append({"role": "user", "content": user_message})

        payload = {
            "model": self.model,
            "messages": self._messages,
            "stream": stream,
        }
        
        if format:
            payload["format"] = format

        try:
            reply = self._call_ollama(payload, stream=stream)
        except Exception:
            self._messages.pop()
            raise

        self._messages.append({"role": "assistant", "content": reply})
        return reply

    def _call_ollama(self, payload: dict, stream: bool) -> str:
        req = urllib.request.Request(
            f"{self.base_url}/api/chat",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )

        try:
            with urllib.request.urlopen(req) as resp:
                if stream:
                    full_reply = ""
                    for line in resp:
                        if line:
                            chunk = json.loads(line.decode("utf-8"))
                            content = chunk.get("message", {}).get("content", "")
                            print(content, end="", flush=True)
                            full_reply += content
                    print()
                    return full_reply
                else:
                    data = json.loads(resp.read().decode("utf-8"))
                    return data.get("message", {}).get("content", "")
        except urllib.error.URLError as e:
            raise RuntimeError(f"Ollama connection failed: {e}")

# ── Gemini Connector ───────────────────────────────────────────────────────────

class GeminiSession(BaseConversationSession):
    """Conversational session using Google's Gemini API."""
    
    def __init__(self, model: str, system_prompt: Optional[str] = None):
        super().__init__(model, system_prompt)
        
        try:
            from google import genai
            self.client = genai.Client() # Automatically picks up GEMINI_API_KEY
        except ImportError:
            raise ImportError("Please install google-genai: pip install google-genai")
        except Exception as e:
            raise RuntimeError(f"Failed to initialize Gemini Client. Did you set GEMINI_API_KEY? Error: {e}")
            
        self._chat_session = None
        self.reset()

    def reset(self):
        from google import genai
        
        # Configure system prompt if provided
        config = None
        if self.system_prompt:
            config = genai.types.GenerateContentConfig(
                system_instruction=self.system_prompt,
            )
            
        self._chat_session = self.client.chats.create(
            model=self.model,
            config=config
        )

    def chat(self, user_message: str, *, stream: bool = False) -> str:
        if stream:
            response = self._chat_session.send_message_stream(user_message)
            full_reply = ""
            for chunk in response:
                print(chunk.text, end="", flush=True)
                full_reply += chunk.text
            print()
            return full_reply
        else:
            response = self._chat_session.send_message(user_message)
            return response.text

# ── Factory Function ───────────────────────────────────────────────────────────

def get_conversation_session(model: str = DEFAULT_MODEL, system_prompt: Optional[str] = None) -> BaseConversationSession:
    """
    Factory function to get the appropriate session connector based on the model name.
    """
    if model in GEMINI_MODELS or model.startswith("gemini"):
        return GeminiSession(model, system_prompt)
    elif model in OLLAMA_MODELS or "llama" in model or "qwen" in model:
        # Fallback to Ollama for anything we don't strictly recognize as Gemini
        return OllamaSession(model, system_prompt)
    else:
        # Default fallback to Ollama
        return OllamaSession(model, system_prompt)

