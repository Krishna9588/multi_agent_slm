# Multi-Agent System: Technical Architecture (v2)

Updated to reflect the full 5-pillar cloud-equivalency infrastructure.

```text
  ┌──────────────────────────────────────────────────────────────────┐
  │                      User / CLI (run.py)                         │
  └─────────────────────────────┬────────────────────────────────────┘
                                │
                  ┌─────────────▼──────────────┐
                  │   Long-Term Memory (Recall) │ ◄── ChromaDB / JSON fallback
                  │      memory_store.py        │     Injects past context on start
                  └─────────────┬──────────────┘
                                │
  ┌─────────────────────────────▼────────────────────────────────────┐
  │                      Orchestrator Agent                          │
  │                       (core/orchestrator.py)                     │
  │                                                                  │
  │  ┌────────────────────────────────────────────────────────────┐  │
  │  │              Blackboard (memory/blackboard.py)             │  │
  │  │  scraped_text | scraped_url | ner_results | step_log ...   │  │
  │  └────────────────────────────────────────────────────────────┘  │
  │                                                                  │
  │  ┌──────────────────────────────────────────────────────────┐    │
  │  │              ReAct Loop (format="json" enforced)         │    │
  │  │  Thought → Action → Observation → Repeat / Final Answer  │    │
  │  └──────────────────────────────────────────────────────────┘    │
  └───────────┬──────────────┬──────────────────┬────────────────────┘
              │              │                  │
              ▼              ▼                  ▼
  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────────────┐
  │ Discovery Layer │ │   Web Layer     │ │    Analysis Group       │
  │ (search_agent)  │ │ (web_scraper /  │ │ (ner_agent, sentiment,  │
  │                 │ │ link_extractor) │ │  topic_modeling,        │
  │ DuckDuckGo ──►  │ │                 │ │  page_classifier)       │
  │ Wikipedia   ──► │ │ trafilatura     │ │                         │
  │ ArXiv       ──► │ │ (content trim)  │ │ Pydantic schemas        │
  └────────┬────────┘ └────────┬────────┘ │ (agents/schemas.py)     │
           │                   │          └────────────┬────────────┘
           └───────────────────┼───────────────────────┘
                               │
                               ▼
               ┌───────────────────────────────┐
               │     HITL Gateway (Pillar 5)   │ ◄── Pauses for Y/n before
               │  [Confirm high-impact tools]  │     data_exporter runs
               └───────────────┬───────────────┘
                               │
                               ▼
               ┌───────────────────────────────┐
               │      Data Exporter Agent      │ ◄── Saves CSV/JSON to
               │   (data_exporter_agent.py)    │     archive/outputs/
               └───────────────┬───────────────┘
                               │
               ┌───────────────▼───────────────┐
               │   Long-Term Memory (Save)     │ ◄── ChromaDB / JSON fallback
               │      memory_store.py          │     Persists session for recall
               └───────────────────────────────┘
```

## Component Map

| Component | File | Pillar |
|---|---|---|
| Smart Search Gateway | `agents/search_agent.py` | 1 — Discovery |
| Pydantic Output Schemas | `agents/schemas.py` | 2 — JSON Enforcer |
| JSON Retry + Validation | `agents/_base.py` | 2 — JSON Enforcer |
| Content Boilerplate Remover | `agents/web_scraper.py` (trafilatura) | 3 — Content Trimmer |
| Session Blackboard | `memory/blackboard.py` | 4 — State |
| Long-Term Vector Memory | `memory/memory_store.py` (ChromaDB) | 4 — Memory |
| HITL Confirmation Gate | `core/orchestrator.py` (HITL_TOOLS) | 5 — Human-in-Loop |

## Query Routing Logic (search_agent)

```
Query: "Who is Tim Cook?"        → Wikipedia  (factual signal: "who is")
Query: "attention mechanism paper" → ArXiv   (research signal: "paper", "attention")
Query: "Tesla stock price today"   → DuckDuckGo (general/live web)
```

## Data Flow Example

1. **User**: "Search for AI news and save key entities to CSV"
2. **Orchestrator** recalls memory: "Past similar task: AI analysis of TechCrunch..."
3. **search_agent** → DuckDuckGo → returns 4 URLs
4. **web_scraper** → trafilatura strips boilerplate → clean article text on Blackboard
5. **ner_agent** reads Blackboard → extracts entities → validates against `NEROutput` schema
6. **HITL gate** → "data_exporter_agent is a high-impact tool. Proceed? [Y/n]"
7. **data_exporter_agent** → writes `archive/outputs/ai_news_20260630.csv`
8. **Orchestrator** saves session to ChromaDB for future recall
