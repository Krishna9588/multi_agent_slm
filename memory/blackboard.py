"""
memory/blackboard.py
---------------------
Pillar 4A: In-session shared state store (the "Blackboard" pattern).

In a multi-agent system, agents should never pass data to each other directly.
Instead, they READ from and WRITE TO a central shared state (the blackboard).
The Orchestrator owns the blackboard and injects it into each agent call.

Key slots:
  - scraped_text: Raw text from the most recent web_scraper call.
  - scraped_url:  URL that was last scraped.
  - search_results: Last results from search_agent.
  - ner_results:    Structured entities from ner_agent.
  - sentiment:      Sentiment analysis output.
  - classifier:     Page classification output.
  - topics:         Topic modeling output.
  - export_path:    Path to last exported file.
  - user_task:      The current user task string.
  - step_log:       List of all tool calls and their results in this session.
"""

from __future__ import annotations
from typing import Any, Optional
import json
import os
from datetime import datetime


class Blackboard:
    """
    Central shared state dictionary for a single orchestration session.
    Agents read from and write to named slots on this board.
    """

    # Known slot names (for documentation purposes; the board accepts any key)
    SCRAPED_TEXT    = "scraped_text"
    SCRAPED_URL     = "scraped_url"
    SEARCH_RESULTS  = "search_results"
    NER_RESULTS     = "ner_results"
    SENTIMENT       = "sentiment"
    CLASSIFIER      = "classifier"
    TOPICS          = "topics"
    EXPORT_PATH     = "export_path"
    USER_TASK       = "user_task"
    STEP_LOG        = "step_log"

    def __init__(self):
        self._state: dict[str, Any] = {}
        self._state[self.STEP_LOG] = []

    # ── Read/Write ──────────────────────────────────────────────────────────────

    def write(self, slot: str, value: Any) -> None:
        """Write a value to a named slot."""
        self._state[slot] = value

    def read(self, slot: str, default: Any = None) -> Any:
        """Read a value from a named slot. Returns default if not set."""
        return self._state.get(slot, default)

    def log_step(self, tool_name: str, args: dict, result: dict) -> None:
        """Append a completed tool call to the step log."""
        self._state[self.STEP_LOG].append({
            "timestamp": datetime.now().isoformat(),
            "tool": tool_name,
            "args": {k: (v[:200] + "...") if isinstance(v, str) and len(v) > 200 else v for k, v in args.items()},
            "result_keys": list(result.keys()),
            "error": result.get("error"),
        })

    def clear(self) -> None:
        """Reset the blackboard for a new task (keeps step_log history)."""
        history = self._state.get(self.STEP_LOG, [])
        self._state = {}
        self._state[self.STEP_LOG] = history

    def snapshot(self) -> dict:
        """Return a serializable snapshot of the current state (for debugging)."""
        safe = {}
        for k, v in self._state.items():
            if isinstance(v, str) and len(v) > 500:
                safe[k] = v[:500] + "... [truncated]"
            else:
                safe[k] = v
        return safe

    def __repr__(self) -> str:
        keys = [k for k in self._state if k != self.STEP_LOG]
        return f"<Blackboard slots={keys} steps={len(self._state.get(self.STEP_LOG, []))}>"
