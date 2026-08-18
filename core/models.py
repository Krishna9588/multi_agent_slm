"""
Model Connectors
-----------------
Provides a unified ConversationSession interface for both local Ollama and cloud Gemini models.
Maintains conversation history for the session so the orchestrator and agents
don't need to manually manage context.

Supported models:
- llama3.1:8b (Ollama default orchestrator)
- llama3.2:3b (Ollama default sub-agent)
- llama3.2-vision (Ollama default vision)
- qwen2.5:7b, qwen2.5:3b, mistral, gemma2, etc. (Ollama)
- gemini-2.5-flash, gemini-2.5-flash-lite, gemini-1.5-flash (Gemini via google-genai)
"""

import json
import os
import urllib.request
import urllib.error
from typing import Optional, List, Any
from dotenv import load_dotenv

# Load environment variables from .env file (for GEMINI_API_KEY, custom models, etc.)
load_dotenv()

# ── Configuration ──────────────────────────────────────────────────────────────

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

# Defaults are aligned with official documentation and lightweight local SLM usage
DEFAULT_MODEL   = os.getenv("ORCHESTRATOR_MODEL", os.getenv("DEFAULT_MODEL", "llama3.1:8b"))
SECONDARY_MODEL = os.getenv("SUB_AGENT_MODEL", os.getenv("SECONDARY_MODEL", "llama3.2:3b"))
VERIFIER_MODEL  = os.getenv("VERIFIER_MODEL", "llama3.1:8b")
VISION_MODEL    = os.getenv("VISION_MODEL", "llama3.2-vision")

# List of known Ollama models
OLLAMA_MODELS = [
    "llama3.1:8b",
    "llama3.2:3b",
    "llama3.2:1b",
    "llama3.2-vision",
    "llama3:8b",
    "qwen2.5:7b",
    "qwen2.5:3b",
    "qwen2.5:1.5b",
    "phi4-mini:3.8b",
    "phi3:mini",
    "mistral:7b",
    "gemma2:9b",
    "gemma2:2b",
]

GEMINI_MODELS = [
    "gemini-3.1-flash-lite",
    "gemini-3.5-flash-lite",
    "gemini-2.5-flash",
    "gemini-2.5-pro",
    "gemini-1.5-flash",
    "gemini-1.5-pro",
    "gemini-2.0-flash"
]


def is_ollama_running(base_url: str = OLLAMA_BASE_URL, timeout: float = 1.5) -> bool:
    """Checks whether the local Ollama daemon is currently responsive."""
    try:
        req = urllib.request.Request(f"{base_url}/api/tags")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status == 200
    except Exception:
        return False


def get_available_ollama_models(base_url: str = OLLAMA_BASE_URL, timeout: float = 1.5) -> List[str]:
    """Queries Ollama for the list of pulled/installed local models."""
    try:
        req = urllib.request.Request(f"{base_url}/api/tags")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return [m.get("name", "") for m in data.get("models", []) if m.get("name")]
    except Exception:
        return []


# ── Base Interface ─────────────────────────────────────────────────────────────

class BaseConversationSession:
    """Base interface for all conversational models."""
    def __init__(self, model: str, system_prompt: Optional[str] = None):
        self.model = model
        self.system_prompt = system_prompt

    def chat(self, user_message: str, *, stream: bool = False, format: Optional[str] = None, images: Optional[List[str]] = None) -> str:
        raise NotImplementedError

    def reset(self):
        raise NotImplementedError

    def set_system_prompt(self, new_prompt: str):
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

    def set_system_prompt(self, new_prompt: str):
        self.system_prompt = new_prompt
        if self._messages and self._messages[0].get("role") == "system":
            self._messages[0]["content"] = new_prompt
        elif not self._messages:
            self._messages.append({"role": "system", "content": new_prompt})
        else:
            self._messages.insert(0, {"role": "system", "content": new_prompt})

    def chat(self, user_message: str, *, stream: bool = False, format: Optional[str] = None, images: Optional[List[str]] = None) -> str:
        msg: dict[str, Any] = {"role": "user", "content": user_message}
        if images:
            msg["images"] = images
        self._messages.append(msg)

        payload = {
            "model": self.model,
            "messages": self._messages,
            "stream": stream,
            "options": {
                "num_ctx": 16384
            }
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
            with urllib.request.urlopen(req, timeout=120) as resp:
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
        except urllib.error.HTTPError as e:
            if e.code == 404:
                raise RuntimeError(
                    f"Model '{self.model}' is not installed in Ollama.\n"
                    f"Run `ollama pull {self.model}` in your terminal to download it."
                )
            raise RuntimeError(f"Ollama server HTTP {e.code} error: {e.reason}")
        except urllib.error.URLError as e:
            raise RuntimeError(
                f"Cannot connect to Ollama at {self.base_url} ({e.reason}).\n"
                f"Make sure Ollama is running (`ollama serve`) or use cloud mode with `python run.py --premium`."
            )


# ── Gemini Connector ───────────────────────────────────────────────────────────

class GeminiSession(BaseConversationSession):
    """Conversational session using Google's Gemini API."""
    
    def __init__(self, model: str, system_prompt: Optional[str] = None):
        super().__init__(model, system_prompt)
        
        # Discover all available GEMINI API keys
        self.api_keys = []
        for key, val in os.environ.items():
            if key == "GEMINI_API_KEY" or key.startswith("GEMINI_API_KEY_"):
                val = val.strip()
                if val and val != "your_gemini_api_key_here":
                    self.api_keys.append(val)
                    
        # Sort so that GEMINI_API_KEY comes first, then _1, _2, etc.
        self.api_keys.sort(key=lambda k: 0 if k == os.environ.get("GEMINI_API_KEY") else 1)
        
        if not self.api_keys:
            raise RuntimeError(
                "No GEMINI_API_KEY found in environment or .env file.\n"
                "Please add `GEMINI_API_KEY=your_key` to .env to use Gemini models."
            )
            
        self.current_key_idx = 0
        
        try:
            from google import genai
            self.client = genai.Client(api_key=self.api_keys[self.current_key_idx])
        except ImportError:
            raise ImportError("Please install google-genai: pip install google-genai")
        except Exception as e:
            raise RuntimeError(f"Failed to initialize Gemini Client. Error: {e}")
            
        self._chat_session: Any = None
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

    def set_system_prompt(self, new_prompt: str):
        self.system_prompt = new_prompt

    def chat(self, user_message: str, *, stream: bool = False, format: Optional[str] = None, images: Optional[List[str]] = None) -> str:
        from google import genai
        
        config_kwargs: dict[str, Any] = {}
        if format == "json":
            config_kwargs["response_mime_type"] = "application/json"
        if self.system_prompt:
            config_kwargs["system_instruction"] = self.system_prompt
            
        config = None
        if config_kwargs:
            config = genai.types.GenerateContentConfig(**config_kwargs)

        # Retry logic for key rotation and rate limits
        last_error = None
        for _ in range(15):
            try:
                if stream:
                    response = self._chat_session.send_message_stream(user_message, config=config)
                    full_reply = ""
                    for chunk in response:
                        print(chunk.text, end="", flush=True)
                        full_reply += chunk.text
                    print()
                    return full_reply
                else:
                    response = self._chat_session.send_message(user_message, config=config)
                    return response.text
                    
            except Exception as e:
                last_error = e
                print(f"\n  [Models] ⚠️ Gemini request failed: {e}")
                
                if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                    import time
                    print("  [Models] ⏳ Rate limit hit! Sleeping for 15 seconds before retrying...")
                    time.sleep(15)
                    continue
                
                if len(self.api_keys) > 1:
                    self.current_key_idx = (self.current_key_idx + 1) % len(self.api_keys)
                    print(f"  [Models] 🔄 Rotating to next GEMINI_API_KEY (index {self.current_key_idx}) and retrying...")
                    
                    self.client = genai.Client(api_key=self.api_keys[self.current_key_idx])
                    self._chat_session = self.client.chats.create(model=self.model, config=config)
                else:
                    raise e
                    
        raise RuntimeError(f"All retries failed. Last error: {last_error}")


# ── Factory Function ───────────────────────────────────────────────────────────

def get_conversation_session(model: str = DEFAULT_MODEL, system_prompt: Optional[str] = None) -> BaseConversationSession:
    """
    Factory function to get the appropriate session connector based on the model name.
    """
    if model in GEMINI_MODELS or model.startswith("gemini"):
        return GeminiSession(model, system_prompt)
    else:
        # Default to Ollama for local models
        return OllamaSession(model, system_prompt)


def get_lc_model(role: str = "default"):
    """
    LangChain model factory returning a BaseChatModel instance based on role.
    Gracefully imports from langchain_ollama or langchain_community.
    """
    model_map = {
        "default":   DEFAULT_MODEL,
        "secondary": SECONDARY_MODEL,
        "verifier":  VERIFIER_MODEL,
    }
    model_name = model_map.get(role, DEFAULT_MODEL)

    if model_name in GEMINI_MODELS or model_name.startswith("gemini"):
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
            return ChatGoogleGenerativeAI(model=model_name)
        except ImportError:
            try:
                from langchain_community.chat_models import ChatGoogleGenerativeAI
                return ChatGoogleGenerativeAI(model=model_name)
            except ImportError:
                raise ImportError("Please install langchain-google-genai: pip install langchain-google-genai")
    else:
        try:
            from langchain_ollama import ChatOllama
            return ChatOllama(model=model_name, temperature=0, base_url=OLLAMA_BASE_URL)
        except ImportError:
            try:
                from langchain_community.chat_models import ChatOllama
                return ChatOllama(model=model_name, temperature=0, base_url=OLLAMA_BASE_URL)
            except ImportError:
                raise ImportError(
                    "Please install langchain-community or langchain-ollama: pip install langchain-community"
                )

