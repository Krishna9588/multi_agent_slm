# Multi-Agent System (MAS) — Architecture & Design Document

This document outlines the foundational architecture and future scalability plan for our dynamic, multi-agent system. It is designed to be easily extensible, meaning anyone can take this foundation and reshape it to their specific needs.

---

## 1. Problem Scoping and Objective Definition

**Objective:** 
Build a dynamic, highly extensible, and scalable Multi-Agent System (MAS). The system must be capable of running locally for privacy and cost-efficiency (via Ollama) while being instantly switchable to cloud-based frontier models (via Gemini) for heavy-duty reasoning.

**Core Problem Solved:** 
Traditional agent frameworks are often overly rigid or excessively bloated. This system provides a clean, auto-discovering foundation where developers can simply drop a new Python file into the `agents/` folder, and the central Orchestrator immediately learns how to use it.

**Future Integrations:**
- **LangChain / LlamaIndex**: To access pre-built document loaders and vector stores.
- **LangSmith**: For observability, debugging, and tracing the exact thought processes of the Orchestrator.

---

## 2. Defining Agent Roles and Personas

To prevent the LLM from becoming confused, every agent must have a strictly defined boundary, persona, and output schema. 

### **Currently Implemented Agents**
- `web_scraper`: The data gatherer (5-strategy cascading waterfall). Auto-detects anti-bot measures and hands off to `browser_agent`.
- `browser_agent`: A Playwright-powered Set-of-Mark agent that interacts with dynamic pages using integer element IDs to eliminate CSS hallucination.
- `auth_agent`: Securely logs into platforms (LinkedIn/GitHub) using .env credentials and saves session state for the browser agent.
- `vision_agent`: Multimodal agent (`llama3.2-vision`) that solves CAPTCHAs and analyses UI screenshots.
- `memory_agent`: Interfaces with a Vector Database (ChromaDB/FAISS) to actively store and recall scraped facts or user preferences.
- `qa_agent`: A Critic agent that evaluates JSON output for hallucinations or missing fields before returning it to the user.
- `code_executor_agent`: A secure Python execution sandbox running inside an isolated Docker container (`python:3.10-slim`).
- `ner_agent`, `page_classifier`, `topic_modeling`, `sentiment_analysis`: Standard NLP processing agents.

### **Proposed New Agents & Connectors**
1. **`research_agent`**: Has access to search engines (e.g., Tavily or DuckDuckGo API) to actively hunt for information across the web.
2. **`writer_agent`**: Specialises in taking raw JSON data from other agents and formatting it into human-readable reports, emails, or markdown.

---

## 3. Architecting the "Smart Routing" and System Flow

The system currently uses a pure **ReAct (Reasoning + Acting)** pattern. As the system scales, relying solely on ReAct can lead to token limits and infinite loops. We will evolve the flow into a **Hierarchical Supervisor Network**.

**The Flow Design (TransferToAgent Protocol):**
1. **User Request** → Enters the API.
2. **Dynamic Tool Selector (Pre-processing):** A lightweight prompt asks the model to pick only the 3-4 tools required for the task. This massively reduces cognitive load and prevents hallucination loops.
3. **Supervisor Orchestrator:** The main reasoning engine (e.g., Gemini 2.5 Flash via `--premium` or local Llama 3.1). It breaks the complex task into a DAG (Directed Acyclic Graph) of sub-tasks.
4. **Sub-Agent Execution (Swarm Router):** If the Supervisor assigns a complex, multi-step stateful task (like navigating Hacker News), the target agent returns a `TransferToAgent` signal. The Orchestrator instantly pauses its ReAct loop, boots up the Swarm Router for the sub-agent, and yields control.
5. **Critique / Verification:** Before returning the final answer, the `qa_agent` (Critic) verifies the output against the original user prompt, forcing the Swarm to fix issues dynamically.

*(Note: We can implement this complex routing using **LangGraph**, which is perfect for building cyclic and stateful multi-agent applications).*

---

## 4. Designing the Data Pipeline

As the system moves towards a cloud-ready deployment, the way data moves between agents must be standardized.

1. **State Management (Context):** 
   - Moving from passing around raw Python strings to a structured **State Dictionary** (similar to LangGraph). 
   - We will define Pydantic models for the data flowing between agents so we never encounter parsing errors.
2. **Long-Term Memory:**
   - Integration with a local Vector DB (e.g., **ChromaDB** or **Qdrant**) to store user preferences and past analyses.
3. **Observability (LangSmith):**
   - Every agent execution, LLM call, and tool result will be wrapped in a tracer. This allows us to view a UI dashboard showing exactly how many tokens were used, how long the web scraper took, and why the Orchestrator made a specific decision.

---

## 5. Defining the Tech Stack and Interfaces

To make this easily deployable on cloud providers (AWS, GCP, or Render), the architecture will be standardized around the following stack:

- **Core Language:** Python 3.10+
- **LLM Connectors:** Custom unified interface (`models.py`) wrapped in standard LangChain `BaseChatModel` classes.
- **Data Validation:** `pydantic` (V2) to enforce strict schema adherence for all JSON outputs.
- **Observability:** `langsmith` and `langchain-core` for tracing.
- **API Layer (Next Step):** Wrap `run.py` in a **FastAPI** server. Instead of just a CLI, the system will expose `/chat` and `/task` endpoints that stream Server-Sent Events (SSE) to a frontend.
- **Containerization:** A `docker-compose.yml` that provides a local isolated `browserless/chrome` sandbox.
- **Cloud Fallback (E2B):** If local Docker is unavailable, the system uses the `e2b` Python SDK to spin up a secure, ephemeral cloud sandbox for web navigation, protecting the host network.

---

## Next Actionable Steps for Implementation:
1. Wrap our current `models.py` sessions into LangChain-compatible interfaces to unlock the ecosystem.
2. Introduce Pydantic to our agents so we don't have to rely on regex to parse JSON.
3. Build the FastAPI wrapper to expose the orchestrator as a web service.
4. Implement LangSmith tracing in the orchestrator loop.
