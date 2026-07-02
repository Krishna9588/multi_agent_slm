# Changelog

All notable changes to the Unified AI System are documented here.

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
