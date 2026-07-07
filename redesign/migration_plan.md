# System Redesign & Migration Plan: 100% Local, Zero-Cost Architecture

## Goal Description
The current system relies heavily on paid APIs (Gemini, Apify, E2B Cloud Sandbox) which leads to rate limits, execution deadlocks, and unnecessary costs. The goal of this redesign is to migrate the entire system to a **100% local, zero-cost, open-source architecture** leveraging Ollama for LLM execution, local Playwright for browser scraping, and local Docker for code execution. We will evaluate and adopt either LangChain/LangGraph or Microsoft AutoGen for the core multi-agent orchestration.

## Framework Evaluation: LangChain vs AutoGen

| Feature | LangChain / LangGraph | Microsoft AutoGen |
| :--- | :--- | :--- |
| **Agent Paradigm** | Single-agent tool loops or DAG (Directed Acyclic Graph) state machines. | Conversational agents that chat with each other to solve problems. |
| **Local LLM Support** | Native `ChatOllama` integration. Very stable. | Supported via LiteLLM proxy or OpenAI compatible endpoints (`localhost:11434/v1`). |
| **Tool Calling** | Native `@tool` decorators with schema extraction. | Function calling via JSON schemas injected into system prompts. |
| **Memory Management** | Built-in `MemorySaver` checkpointers (SQLite, Postgres). | Memory is maintained in the conversation history array between agents. |
| **Best For** | Predictable, step-by-step pipelines (e.g., scrape -> extract -> analyze -> save). | Open-ended problem solving and code generation where agents debate/refine. |

## Replacing Paid/External Dependencies (Zero-Cost Migration)

| Current Factor | Current Implementation (Paid/Cloud) | Proposed Replacement (100% Local) |
| :--- | :--- | :--- |
| **Core LLM Engine** | Google Gemini 2.5 Flash API | **Ollama** (`llama3.1`, `qwen3.5`, `gemma2`) running locally. |
| **Cost / Credits** | Pay-per-token or strict Free-Tier quotas. | **$0 / Unlimited**. Limited only by local machine hardware/time. |
| **Complex Scraping** | Apify, BrightData API tokens. | **Local Playwright** (`browser_agent`) running in headless mode. |
| **Code Sandbox** | E2B Cloud Sandbox API. | **Local Docker** (`docker-compose up browser-sandbox`). |
| **Observability** | LangSmith (requires API key). | **Local file-based logging** or standard stdout trace loops. |
| **Memory** | Volatile or external DBs. | **Local SQLite** database for persistence. |

## Migration Execution Steps

We will create a `redesign` folder in the root directory to build the new architecture cleanly without breaking the existing scripts.

1. **`redesign/architecture_spec.md`**
   A complete technical blueprint of the new system, detailing the exact agent topology, memory persistence layer, and tool wrappers.
2. **`redesign/orchestrator.py`**
   The new main loop using the chosen framework (LangChain or AutoGen), strictly hardcoded to only utilize `localhost:11434` for Ollama.
3. **`redesign/local_tools.py`**
   A reimagined tools module that completely removes all API dependencies, relying solely on local Python libraries (`BeautifulSoup`, `Playwright`, `urllib`).
