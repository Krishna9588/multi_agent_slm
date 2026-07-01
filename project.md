# Ollama Dynamic Multi-Agent System

> **Model**: `llama3.1:8b` running locally via [Ollama](https://ollama.com)
> **No cloud API. No external Python packages. Pure stdlib + your local GPU.**

---

## Project Structure

```
ollama/
│
├── main.py                      ← ConversationSession (memory client)
│
├── agents/                      ← One file = one agent (add new ones freely)
│   ├── __init__.py              ← Auto-discovery registry (REGISTRY dict)
│   ├── _base.py                 ← Shared LLM utilities (private, not an agent)
│   ├── web_scraper.py           → def web_scraper(url)
│   ├── link_extractor.py        → def link_extractor(url)
│   ├── page_classifier.py       → def page_classifier(text)
│   ├── ner_agent.py             → def ner_agent(text)
│   ├── topic_modeling.py        → def topic_modeling(text)
│   └── sentiment_analysis.py   → def sentiment_analysis(text)
│
├── orchestrator.py              ← Dynamic LLM-driven ReAct orchestrator
├── run.py                       ← CLI entry point
│
├── main.py                      ← Original conversational chat client
└── web_agents.py                ← Original monolithic agent script
```

---

## How to Run

```bash
# 1. Make sure Ollama is running
ollama serve

# 2. Pull the model (one-time)
ollama pull llama3.1:8b

# 3a. Interactive session
python run.py

# 3b. One-shot task
python run.py "Analyse https://proplusdata.co and find their services"
python run.py "Extract all links from https://ollama.com"
python run.py "What is the sentiment of https://python.org/about"

# 3c. List all registered agents
python run.py --list-agents
```

### Interactive Commands
| Command   | Effect                                      |
|-----------|---------------------------------------------|
| `/agents` | List all registered agents + descriptions   |
| `/save`   | Save last task's tool results → results.json|
| `/reset`  | Fresh orchestrator session                  |
| `/quit`   | Exit                                        |

---

## The Agent File Convention

Every file in `agents/` must follow this pattern:

```python
# agents/my_new_agent.py

DESCRIPTION = "What this agent does (shown to the LLM orchestrator)"

PARAMETERS = {
    "input_arg": {
        "type": "string",
        "required": True,
        "description": "What this argument is for",
    }
}

def my_new_agent(input_arg: str) -> dict:
    # function name = filename (no .py)
    ...
    return {"result": ...}
```

That is all. The next time you run the system, `__init__.py` auto-discovers it —
no imports, no registration files to update.

---

## How the Orchestrator Works (ReAct Pattern)

```
User: "Crawl https://proplusdata.co and find their services and social media"
  │
  ▼
Orchestrator sends to LLM:
  "You have these tools: web_scraper, link_extractor, page_classifier,
   ner_agent, topic_modeling, sentiment_analysis. Plan your steps."
  │
  ▼ LLM responds:
  {"action": "call_tool", "tool": "web_scraper", "args": {"url": "https://proplusdata.co"}}
  │
  ▼ Python executes web_scraper() for real, returns actual page content
  │
  ▼ Result fed back to LLM
  │
  ▼ LLM responds:
  {"action": "call_tool", "tool": "ner_agent", "args": {"text": "$scraped_text"}}
  │
  ▼ Python resolves $scraped_text → actual text, calls ner_agent()
  │
  ▼ LLM responds:
  {"action": "call_tool", "tool": "link_extractor", "args": {"url": "https://proplusdata.co"}}
  │
  ▼ Python executes link_extractor() → real links from the page
  │
  ▼ LLM responds:
  {"action": "final_answer", "answer": "proplusdata.co offers: ...  Social: LinkedIn: ..."}
  │
  ▼ Done.
```

The LLM decides what to do at each step. **No hard-coded pipeline.**

---

## Registered Agents

| File | Function | Type | Input | Output |
|------|----------|------|-------|--------|
| `web_scraper.py` | `web_scraper(url)` | Python (no LLM) | URL | title, text, word_count |
| `link_extractor.py` | `link_extractor(url)` | Python (no LLM) | URL | internal/external/social links |
| `page_classifier.py` | `page_classifier(text)` | LLM | plain text | page_type, confidence, reasoning |
| `ner_agent.py` | `ner_agent(text)` | LLM | plain text | people, orgs, locations, products, technologies |
| `topic_modeling.py` | `topic_modeling(text)` | LLM | plain text | primary_topic, secondary_topics, keywords, summary |
| `sentiment_analysis.py` | `sentiment_analysis(text)` | LLM | plain text | sentiment, confidence, tone, intent, key_phrases |

---

## Why Local LLM = Unlimited Requests

Cloud APIs (OpenAI, Anthropic) charge per token and have rate limits.
With Ollama on your local machine:
- Every ReAct loop step costs $0
- You can run 50 agents on one page without worrying
- The orchestrator can run as many sub-tasks as needed

This is the foundation for building complex, deeply integrated AI workflows.

---

## Adding More Agents (Future Ideas)

| Agent idea | File name |
|---|---|
| PDF text extractor | `pdf_extractor.py` → `def pdf_extractor(path)` |
| Contact info finder | `contact_finder.py` → `def contact_finder(text)` |
| Competitor detector | `competitor_finder.py` → `def competitor_finder(text)` |
| Language detector | `language_detector.py` → `def language_detector(text)` |
| Price scraper | `price_scraper.py` → `def price_scraper(url)` |
| Email harvester | `email_extractor.py` → `def email_extractor(text)` |

Just create the file, follow the convention, and it's live on the next run.
