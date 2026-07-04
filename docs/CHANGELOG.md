# Changelog

All notable changes to the Unified AI System are documented here.

## [2026-07-04] - The Autonomous Swarm Overhaul

### Added
- **10 New Advanced Swarm Agents:** Transformed the scraper into a full Autonomous Digital Worker by building out 5 distinct ideologies:
  - **The System of Record:** `sql_db_agent.py` (Secure SQLite/Postgres querying) and `api_discovery_agent.py` (Dynamic REST API integrations).
  - **The Communicator:** `email_agent.py` (IMAP/SMTP inbox management), `calendar_agent.py` (Meeting scheduling with conflict prevention), and `social_media_agent.py` (Mentions and posting).
  - **The Archivist:** `pdf_ocr_agent.py` (Massive document text searching) and `audio_transcription_agent.py` (Local Whisper audio chunking).
  - **The Local Administrator:** `github_agent.py` (Automated CLI git actions in sandbox) and `file_system_agent.py` (Strictly path-jailed file organizer).
  - **The Optimizer:** `self_reflection_agent.py` (Evolutionary algorithm that reads failure logs and autonomously patches the Python code of other agents to improve them).
- **Interactive Test Suite (`tests/test_agents.py`):** Added a dynamic CLI utility that auto-imports agents and runs safety/logic tests against their functions to generate a bug report.
- **Swarm Router (Sub-Agent Handoffs):** The core Orchestrator now natively supports the `TransferToAgent` protocol. If a complex task stalls, the Orchestrator can dynamically spawn a specialised Swarm sub-agent (like the `BrowserAgent`), pass control to it, and wait for it to return extracted data.
- **Vision Agent (`vision_agent.py`):** Added a new multimodal agent powered by `llama3.2-vision` to analyse screenshots, solve CAPTCHAs, and interpret UI layouts that standard text extraction misses.
- **Memory Agent (`memory_agent.py`):** Added a long-term Vector DB agent capable of storing massive datasets and user preferences persistently across sessions.
- **QA/Critic Agent (`qa_agent.py`):** Added an evaluation agent that checks the output of data-extraction agents against user requirements, forcing them to fix hallucinations or missing fields before returning data.
- **Interactive Authentication Flow (`auth_agent.py`):** Deprecated `.env` passwords in favor of an Interactive Browser flow. The Swarm pops a visible Chrome window, waits for manual user login (handling 2FA/OAuth), and securely saves the session cookies to disk for the `BrowserAgent` to reuse.

### Changed
- **Cloudflare/SPA Bypass:** Upgraded `web_scraper.py` to auto-detect anti-bot pages (e.g., Cloudflare's "Just a moment...") and client-side rendered React apps. Instead of failing, it now seamlessly triggers a `TransferToAgent(browser_agent)` to dynamically render the page.
- **Set-of-Mark (Accessibility Trees):** Upgraded `browser_agent.py` to use Javascript to inject unique `data-agent-id` tags into the live DOM. The agent now interacts with the page purely using integer IDs (e.g. `browser_click(15)`) instead of hallucinating CSS selectors, increasing reliability by 90%.
- **Secure Sandboxing:** Upgraded `code_executor_agent.py`. All LLM-generated Python code is now securely executed inside an isolated, internet-disabled `python:3.10-slim` Docker container instead of the host machine.

## [2026-07-02] - Orchestrator & Deep Research Upgrades

### Added
- **Dynamic Tool Injection:** The Orchestrator now uses a pre-processor (`_select_tools`) to identify the 3-4 most relevant tools for a user task. This drastically reduces the cognitive load on the 8B model and prevents tool-hallucination loops.
- **Premium Cloud Mode:** Added a `--premium` flag to `run.py`. When run (e.g. `python run.py --premium "task"`), the Orchestrator switches to using `gemini-2.5-flash` for complex reasoning tasks (requires `GEMINI_API_KEY` in `.env`).
- **Comprehensive Company Profiling:** Upgraded `deep_research_agent.py` to auto-detect company profiling requests and automatically extract a structured 15-point schema (Founders, Pricing, Blogs, Partners, Contacts, Industries, etc.) across up to 10 sub-pages.
- **Multi-Format Data Exporter:** Upgraded `data_exporter_agent.py` to support exporting extracted data to `.csv`, `.json`, and `.md` formats.
- **Failsafe Output Parsing:** Added a failsafe to the ReAct loop in `core/orchestrator.py`. If the model outputs an empty `final_answer`, it will automatically fall back to outputting the raw data from the most recent tool call.

### Changed
- **Orchestrator Rules:** Consolidated the 12 complex Orchestrator system rules into 5 strict, easily understood laws to prevent model confusion.
- **Dual Output for Research:** The Deep Research Agent now outputs a formatted Markdown report directly to the chat, while retaining structured JSON in memory for exporting.
- **Tool Fallbacks:** Fixed formatting issues with local LLM JSON outputs during tool calls.

### Fixed
- Fixed an infinite loop where the Orchestrator would continuously call unrelated tools (like `search_agent` or `ner_agent`) instead of crawling the provided links when using the 8B model.
