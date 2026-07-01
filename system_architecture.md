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
- `web_scraper`: The data gatherer (5-strategy cascading waterfall).
- `ner_agent`: Entity extraction (Outputs structured JSON arrays).
- `page_classifier`: Categorises web content.
- `topic_modeling` & `sentiment_analysis`: NLP tasks.

### **Proposed New Agents & Connectors**
1. **`research_agent`**: Has access to search engines (e.g., Tavily or DuckDuckGo API) to actively hunt for information across the web.
2. **`data_analyst_agent`**: A sandbox environment where the LLM can write and execute Pandas/Python code to analyse CSVs or databases.
3. **`memory_agent`**: Interfaces with a Vector Database to recall facts from past conversations.
4. **`writer_agent`**: Specialises in taking raw JSON data from other agents and formatting it into human-readable reports, emails, or markdown.

---

## 3. Architecting the "Smart Routing" and System Flow

The system currently uses a pure **ReAct (Reasoning + Acting)** pattern. As the system scales, relying solely on ReAct can lead to token limits and infinite loops. We will evolve the flow into a **Hierarchical Supervisor Network**.

**The New Flow Design:**
1. **User Request** → Enters the API.
2. **Semantic Router (Fast Routing):** A lightweight embedding model classifies the intent. If the request is simple, it routes it directly to a specific agent. If complex, it goes to the Supervisor.
3. **Supervisor Orchestrator:** The main reasoning engine (e.g., Gemini 2.5 Flash). It breaks the complex task into a DAG (Directed Acyclic Graph) of sub-tasks.
4. **Sub-Agents Execute:** The Supervisor delegates tasks to specialized agents (e.g., `web_scraper` → `ner_agent`).
5. **Critique / Verification:** Before returning the final answer, a lightweight "Critic Agent" verifies the output against the original user prompt.

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
- **Containerization:** A `Dockerfile` and `docker-compose.yml` to spin up Ollama, the Vector DB, and the FastAPI server in one command.

---

## Next Actionable Steps for Implementation:
1. Wrap our current `models.py` sessions into LangChain-compatible interfaces to unlock the ecosystem.
2. Introduce Pydantic to our agents so we don't have to rely on regex to parse JSON.
3. Build the FastAPI wrapper to expose the orchestrator as a web service.
4. Implement LangSmith tracing in the orchestrator loop.
