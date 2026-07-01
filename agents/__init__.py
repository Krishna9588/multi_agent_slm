"""
Agent Registry — auto-discovers every agent in this package.

Convention: every .py file in agents/ must expose:
    - A callable named exactly after the file  (e.g. ner_agent.py → def ner_agent(...))
    - DESCRIPTION : str   — plain-English description shown to the LLM orchestrator
    - PARAMETERS  : dict  — JSON-Schema-style spec of accepted arguments

Adding a new agent:
    1. Create agents/my_new_agent.py
    2. Add DESCRIPTION, PARAMETERS, and def my_new_agent(...)
    3. Done — it is auto-registered at import time, no other changes needed.
"""

import importlib
from pathlib import Path
from typing import Callable

# REGISTRY maps  agent_name → {"fn": callable, "description": str, "parameters": dict}
REGISTRY: dict[str, dict] = {}


def _discover() -> None:
    agents_dir = Path(__file__).parent
    for path in sorted(agents_dir.glob("*.py")):
        if path.stem.startswith("_") or path.stem == "schemas":
            continue                              # skip __init__.py, _private files, and schema definitions
        try:
            module = importlib.import_module(f"agents.{path.stem}")
        except Exception as exc:
            print(f"[agents] WARNING: could not import {path.name}: {exc}")
            continue

        fn: Callable | None = getattr(module, path.stem, None)
        if fn is None:
            print(f"[agents] WARNING: {path.name} has no function named '{path.stem}' — skipped")
            continue

        REGISTRY[path.stem] = {
            "fn":          fn,
            "description": getattr(module, "DESCRIPTION", "(no description)").strip(),
            "parameters":  getattr(module, "PARAMETERS",  {}),
        }


_discover()


def list_agents() -> list[str]:
    """Return sorted list of registered agent names."""
    return sorted(REGISTRY.keys())


def get_agent(name: str) -> dict | None:
    """Return agent entry or None if not found."""
    return REGISTRY.get(name)


def call_agent(name: str, **kwargs):
    """
    Call a registered agent by name.
    Raises KeyError if the agent does not exist.
    Raises TypeError if wrong arguments are passed.
    """
    entry = REGISTRY.get(name)
    if entry is None:
        raise KeyError(f"No agent named '{name}'. Available: {list_agents()}")
    return entry["fn"](**kwargs)
