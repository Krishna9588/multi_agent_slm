# Ollama Multi-Agent System

A fully local, dynamic multi-agent system powered by `llama3.1:8b`. This system uses a ReAct orchestrator to automatically route tasks between multiple specialised agents (like web scrapers, link extractors, and NER extractors) — all running on your local machine without cloud API dependencies.

## 🚀 Step-by-Step Setup

Follow these steps to get the project running.

### 1. Install & Start Ollama
Ensure you have [Ollama](https://ollama.com/) installed on your machine.
Open a terminal and start the server:
```bash
ollama serve
```

### 2. Pull the Model
In a separate terminal, pull the required model (this is a one-time download):
```bash
ollama pull llama3.1:8b
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

## 🛑 Project Structure & Strict Folder Rule

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
