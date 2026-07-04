# Ollama Multi-Agent System

A fully local, dynamic multi-agent system powered by `llama3.1:8b`. This system uses a ReAct orchestrator to automatically route tasks between multiple specialised agents (like web scrapers, link extractors, and NER extractors) — all running on your local machine without cloud API dependencies.

### The Autonomous Swarm Ecosystem
The system has been transformed into a fully Autonomous Digital Worker with 10 specialized, highly integrated agents spanning 5 core capabilities:
- **The System of Record:** `sql_db_agent.py` and `api_discovery_agent.py` for dynamic data fetching.
- **The Communicator:** `email_agent.py`, `calendar_agent.py`, and `social_media_agent.py`.
- **The Archivist:** `pdf_ocr_agent.py` and `audio_transcription_agent.py`.
- **The Local Administrator:** `github_agent.py` and `file_system_agent.py` (with strict path-jails).
- **The Optimizer:** `self_reflection_agent.py` which dynamically rewrites agent Python files based on failure logs.

**For full details on LLM requirements and architecture**, see [docs/models_and_requirements.md](docs/models_and_requirements.md).

## Usage

### 1. The Interactive Testing Suite
We built a dynamic testing utility to ensure all 10 agents are functioning safely.
```bash
python tests/test_agents.py
```
This interactive CLI will allow you to run tests against all agents or specific ones, simulating edge cases (e.g., path traversal attacks, double-booking meetings, database drops) and generating a final report.

### 2. Standard Swarm Execution

## Step-by-Step Setup

Follow these steps to get the project running.

### 1. Install & Start Ollama
Ensure you have [Ollama](https://ollama.com/) installed on your machine.
Open a terminal and start the server:
```bash
ollama serve
```

### 2. System Requirements & Models
This system uses a Multi-Agent Swarm architecture that delegates tasks to specialized models. You will need to install these models locally via Ollama (or use alternatives).

> **📖 Full Guide:** Please read the [System Requirements & Model Selection Guide](docs/models_and_requirements.md) for a detailed breakdown of model comparisons, cloud fallbacks, and `.env` configuration.

**Quick Start Required Models:**
In a separate terminal, pull the required models:
```bash
# 1. The Main Orchestrator (Reasoning & Routing)
ollama pull llama3.1:8b

# 2. The Browser & Swarm Sub-Agents (Fast, lightweight execution)
ollama pull llama3.2:3b

# 3. The Vision Agent (Multimodal CAPTCHA & UI analysis)
ollama pull llama3.2-vision
```

### 3. Setup Python Environment
Make sure you are using Python 3.10+. Create a virtual environment and install dependencies:
```bash
# Create a virtual environment
python -m venv .venv

# Activate it (Windows PowerShell)
.\.venv\Scripts\Activate.ps1

# Install the required packages
pip install -r requirements.txt
```

### 4. Run the System
The **only file you need to run** is `run.py`. 

```bash
# Start an interactive agent session:
python run.py

# Use Premium Cloud Mode for complex multi-step reasoning (Requires GEMINI_API_KEY in .env)
python run.py --premium

# Run a one-shot task:
python run.py "Analyse https://example.com and find any listed companies"

# See all available agents:
python run.py --list-agents
```

---

## Project Structure & Strict Folder Rule

We keep the root directory perfectly clean so it is always obvious what to run.

```text
ollama/
├── run.py                       ← CLI entry point (Run this file!)
├── requirements.txt             
├── README.md                    
├── core/                        ← Core engine (models, orchestrator)
├── agents/                      ← Agent modules
├── memory/                      ← Memory system (ChromaDB, Blackboard)
├── docs/                        ← Architecture documentation
├── scripts/                     ← Utilities (e.g., health_check.py)
└── archive/                     ← Saved outputs and history
```

**CRITICAL RULE FOR CONTRIBUTORS:**
Never place new files in the root directory. 
- New agents go in `agents/`
- Documentation goes in `docs/`
- Scripts go in `scripts/`
- If no relevant folder exists, **create one**.

For deeper architectural details, see the files in the `docs/` directory.
