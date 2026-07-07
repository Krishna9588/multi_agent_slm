# Multi-Model Agents

A fully local, dynamic multi-agent system powered by LLMs running a ReAct orchestration loop.

---

## What is this?

This is a dynamic, multi-agent AI system designed to operate as an autonomous digital worker. Instead of a single LLM trying to execute all workflows, this system uses a **ReAct (Reason-Act) Orchestrator** to dynamically route tasks across a swarm of **28 highly-specialized AI Agents**. 

It can browse the web, write and execute code, clone Git repositories, manage calendars, query databases, and structurally extract data—while autonomously self-correcting and recovering from execution errors.

---

## Tech Stack

Our stack is built for speed, resilience, and maximum autonomy:

- **Core Reasoning Engine**: `llama3.1:8b` via Ollama (ReAct Orchestration)
- **Fast Tool Sub-Agents**: `llama3.2:3b` via Ollama
- **Multimodal Engines**: `llama3.2-vision` & Tesseract (OCR) / ffmpeg (Audio)
- **Browser Automation**: `Playwright` & E2B Cloud Sandboxes
- **Data Engineering**: `markdownify` for structured parsing, Vector Databases for Long-Term Memory
- **Fallback Architecture**: Gemini API integrations for complex reasoning
- **Environment**: Python 3.10+, Dockerized Sandboxing

---

## The 28-Agent Ecosystem

The Orchestrator automatically selects, chains, and manages these specialized agents to solve complex requests autonomously.

### Web & Scraping Division
| Agent | Capability |
|---|---|
| **`browser_agent`** | A full Playwright autopilot. Clicks, scrolls, and navigates SPAs dynamically. |
| **`web_scraper`** | Clean Markdown extraction of any static webpage. |
| **`batch_scraper_agent`** | Concurrently scrapes dozens of deep-links simultaneously via thread pools. |
| **`search_agent`** | Real-time internet search via DuckDuckGo. |
| **`link_extractor`** | Scans pages and extracts every available hyperlink. |
| **`external_service_agent`** | Interfaces with Apify/Bright Data for highly-restricted scraping. |

### Data Processing & AI Logic
| Agent | Capability |
|---|---|
| **`data_structuring_agent`** | Dynamically discovers JSON schemas and extracts unstructured text into structured formats. |
| **`ner_agent`** | Named Entity Recognition (People, Locations, Tech, Products). |
| **`qa_agent`** | Internal Critic. Grades other agents' outputs and forces retries upon hallucination detection. |
| **`sentiment_analysis`** | Analyzes tone and communicative intent. |
| **`topic_modeling`** | Dynamically categorizes large datasets into themes. |
| **`page_classifier`** | Identifies the fundamental nature of a scraped URL. |

### Multimodal Division
| Agent | Capability |
|---|---|
| **`vision_agent`** | Solves CAPTCHAs and reads screenshots/images. |
| **`pdf_ocr_agent`** | Extracts deep text from PDFs and scanned images. |
| **`audio_transcription_agent`** | Transcribes audio and video files locally. |

### Operations & Integrations
| Agent | Capability |
|---|---|
| **`sql_db_agent`** | Inspects SQL schemas, runs queries, and manages DB records. |
| **`github_agent`** | Clones repositories, branches, and commits changes locally. |
| **`api_discovery_agent`** | Dynamically probes and integrates with undocumented REST APIs. |
| **`auth_agent`** | Interactive login handler for authenticated sessions. |
| **`code_executor_agent`** | Sandboxed local Python execution environment. |
| **`file_system_agent`** | Safely organizes, moves, and compresses files in a jailed path. |

### Communications & Research
| Agent | Capability |
|---|---|
| **`email_agent`** | Reads and manages email via OAuth integrations. |
| **`calendar_agent`** | Checks availability and schedules meetings. |
| **`social_media_agent`** | Posts updates and reads mentions across Twitter/LinkedIn. |
| **`deep_research_agent`** | Compound agent for deep profiling across multiple websites. |

### Core System Stability
| Agent | Capability |
|---|---|
| **`memory_agent`** | Vector-based long-term memory to remember past user interactions. |
| **`meta_agent`** | Writes and injects entirely new Python agents into the codebase dynamically. |
| **`self_reflection_agent`** | Analyzes error logs and optimizes failing code. |
| **`setup_guide_agent`** | Onboarding Helper. Reads the rulebooks in `docs/agents/` to guide users through missing API setups. |

---

## Step-by-Step Quick Start

### 1. The Onboarding Rulebooks
We have auto-generated **28 Markdown Rulebooks** in the `docs/agents/` folder. If you ever try to use an agent and lack an API key, the `setup_guide_agent` will catch the error and automatically guide you through the setup process.

### 2. Install & Start Ollama
Ensure you have [Ollama](https://ollama.com/) installed on your machine.
```bash
ollama serve
```

### 3. Pull the Required Models
In a separate terminal, pull the required local models:
```bash
ollama pull llama3.1:8b        # The Main Orchestrator
ollama pull llama3.2:3b        # Sub-Agents
ollama pull llama3.2-vision    # Vision Agent
```

### 4. Setup Python Environment
```bash
python -m venv .venv
source .venv/bin/activate      # Mac/Linux
.\.venv\Scripts\Activate.ps1   # Windows
pip install -r requirements.txt
```

### 5. Run the System
The **only file you need to run** is `run.py`. 

```bash
# Start an interactive autonomous session:
python run.py

# Premium Cloud Mode (Requires GEMINI_API_KEY in .env)
python run.py --premium

# Run a one-shot task:
python run.py "Find Python Jobs in Pune and compile a detailed CSV report."

# Run the safety test suite:
python tests/test_swarm.py
```

---

## Project Structure

```text
multi-agent-system/
├── run.py                 ← Main Orchestrator CLI
├── agents/                ← 28 highly-specialized Swarm Tools
├── core/                  ← ReAct Loop and Model integrations
├── docs/                  
│   └── agents/            ← 28 Auto-Generated Rulebooks for API setups
├── archive/               ← Outputs, scraped CSVs, and logs
├── scripts/               ← Helper utilities and code generators
└── tests/                 ← Execution test suites
```
