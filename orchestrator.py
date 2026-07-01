"""
orchestrator.py — Dynamic LLM-Driven Orchestrator
---------------------------------------------------
Uses the ReAct (Reasoning + Acting) pattern to let the LLM decide which
agents to call and in what order, without any hard-coded pipeline.

How it works:
    1. Build a "tool menu" from the auto-discovered agent REGISTRY
    2. Tell the LLM: "here are your tools, here is the user's task"
    3. LLM responds with JSON: call_tool or final_answer
    4. If call_tool  → execute the real Python agent → feed result back
    5. If final_answer → done, return the answer
    6. Repeat up to MAX_STEPS times

Special variable: $scraped_text
    When the LLM passes "$scraped_text" as a `text` argument, the orchestrator
    automatically substitutes the clean text from the most recent web_scraper
    or link_extractor call. The LLM is told about this in its system prompt.
"""

import json
import sys
import os
from typing import Any

sys.path.insert(0, os.path.dirname(__file__))
import agents
from agents._base import extract_json
from models import get_conversation_session, DEFAULT_MODEL
from memory import Blackboard, save_session, recall_similar, memory_backend
from agents._base import extract_json

# ── Config ─────────────────────────────────────────────────────────────────────

MAX_STEPS     = 20      # max ReAct iterations (prevents infinite loops)
CONTEXT_LIMIT = 800     # max words of a tool result echoed back to the LLM

# Pillar 5: Tools that require human confirmation before execution
HITL_TOOLS = ["data_exporter_agent"]

# ── System prompt builder ──────────────────────────────────────────────────────

def _build_system_prompt() -> str:
    """
    Dynamically builds the orchestrator's system prompt from the agent REGISTRY.
    The LLM gets an accurate, always-up-to-date list of available tools.
    """
    tool_lines: list[str] = []
    for name, entry in sorted(agents.REGISTRY.items()):
        params = entry["parameters"]
        param_str = ", ".join(
            f"{k} ({'required' if v.get('required') else 'optional'}): {v.get('description', '')}"
            for k, v in params.items()
        )
        tool_lines.append(
            f"- {name}({param_str})\n"
            f"  => {entry['description']}"
        )

    tools_block = "\n\n".join(tool_lines)

    return f"""You are an intelligent task orchestrator that coordinates specialised agents to complete user requests.

AVAILABLE TOOLS:
{tools_block}

RULES — follow these exactly:
1. Respond with ONLY valid JSON — no prose, no markdown, no explanations.
2. To call a tool, respond with exactly:
   {{"action": "call_tool", "tool": "<tool_name>", "args": {{<arguments as key-value pairs>}}}}
3. When you have enough information to fully answer the user, respond with exactly:
   {{"action": "final_answer", "answer": "<your complete, well-formatted answer>"}}
4. SPECIAL: when calling a text-analysis tool (page_classifier, ner_agent, topic_modeling, sentiment_analysis),
   pass {{"text": "$scraped_text"}} to reuse the text from the most recent web_scraper call.
   Example: {{"action": "call_tool", "tool": "ner_agent", "args": {{"text": "$scraped_text"}}}}
5. Always call web_scraper or link_extractor BEFORE any text-analysis tool.
6. Choose the minimum necessary tools — do not call tools you don't need.
7. DEEP CRAWLING: If you need to find specific information (like founding members or a specific keyword) and it is not on the current page, use `link_extractor` to find all links, pick the most relevant URL (like About Us, Team, or Contact), and use `web_scraper` on that new URL.
8. EXPORTING: If the user asks to save, extract, or write data to a file (like CSV or Excel), format the data properly and use the `data_exporter_agent`.
9. After receiving tool results, either call another tool OR give a final_answer. Never do both."""


# ── Truncate tool output for context ──────────────────────────────────────────

def _summarise_for_context(result: dict, max_words: int = CONTEXT_LIMIT) -> str:
    """
    Convert a tool result to a compact JSON string for the orchestrator context.
    Long 'text' fields are truncated to prevent context overflow.
    """
    compact = {}
    for k, v in result.items():
        if k == "text" and isinstance(v, str):
            words = v.split()
            if len(words) > max_words:
                compact[k] = " ".join(words[:max_words]) + " [... truncated ...]"
            else:
                compact[k] = v
        elif isinstance(v, list) and len(v) > 20:
            compact[k] = v[:20] + [f"... and {len(v) - 20} more"]
        else:
            compact[k] = v
    return json.dumps(compact, indent=2, ensure_ascii=False)


# ── Orchestrator class ─────────────────────────────────────────────────────────

class Orchestrator:
    """
    LLM-driven orchestrator that runs the ReAct loop.

    Usage:
        orc = Orchestrator()
        answer = orc.run("Analyse https://proplusdata.co and find their services")
        print(answer)
    """

    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        verbose: bool = True,
    ):
        self.model    = model
        self.verbose  = verbose

        # Persistent orchestrator session — accumulates the full ReAct dialogue
        self._session = get_conversation_session(
            model=model,
            system_prompt=_build_system_prompt(),
        )

        # Pillar 4A: Blackboard — shared in-session state for all agents
        self._blackboard = Blackboard()

        # Stores the full (un-truncated) results of each step
        self._step_results: list[dict] = []

        # The most recently scraped text (for $scraped_text substitution)
        self._scraped_text: str = ""
        
        # Track URLs scraped in this session (for memory_store)
        self._scraped_urls: list[str] = []

    # ── Public API ─────────────────────────────────────────────────────────────

    def run(self, user_task: str) -> str:
        """
        Run the ReAct loop for a user task.
        Returns the LLM's final synthesised answer.
        """
        self._step_results.clear()
        self._scraped_text = ""
        self._scraped_urls = []
        self._blackboard.clear()
        self._blackboard.write(Blackboard.USER_TASK, user_task)

        self._log(f"\n{'='*60}")
        self._log(f"  Task: {user_task}")
        self._log(f"{'='*60}")

        # Pillar 4B: Inject relevant long-term memories into first prompt
        memories = recall_similar(user_task, top_k=2)
        memory_context = ""
        if memories:
            snippets = []
            for m in memories:
                snippets.append(f"- Past task: {m['task'][:120]}\n  Summary: {m['answer'][:200]}")
            memory_context = (
                "\n\n[LONG-TERM MEMORY — past relevant sessions:]\n"
                + "\n".join(snippets)
                + "\n[Use this as background context only; re-verify with tools.]"
            )
            self._log(f"  [Memory] Injected {len(memories)} past session(s) as context.")

        # Kick off the loop
        raw = self._session.chat(f"User task: {user_task}{memory_context}", format="json")

        for step in range(1, MAX_STEPS + 1):
            decision = self._parse_decision(raw)

            if decision is None:
                self._log(f"\n[step {step}] Could not parse LLM response, asking it to retry...")
                raw = self._session.chat(
                    "Your response was not valid JSON. "
                    "Respond with ONLY a call_tool or final_answer JSON object.",
                    format="json"
                )
                continue

            action = decision.get("action")

            # ── final_answer ───────────────────────────────────────────────────
            if action == "final_answer":
                answer = decision.get("answer", "(no answer provided)")
                self._log(f"\n[step {step}] → Final answer ready\n")
                # Pillar 4B: Persist session to long-term memory
                save_session(user_task, answer, self._scraped_urls)
                return answer

            # ── call_tool ──────────────────────────────────────────────────────
            if action == "call_tool":
                tool_name = decision.get("tool", "")
                args      = decision.get("args", {})

                self._log(f"\n[step {step}] → Calling: {tool_name}({self._fmt_args(args)})")

                # Pillar 5: HITL gate — pause before high-impact tools
                if tool_name in HITL_TOOLS:
                    self._log(f"\n  [HITL] '{tool_name}' is a high-impact tool.")
                    self._log(f"  [HITL] Proposed args: {self._fmt_args(args)}")
                    try:
                        confirm = input("  Proceed with this action? [Y/n]: ").strip().lower()
                    except (EOFError, KeyboardInterrupt):
                        confirm = "n"
                    if confirm == "n":
                        self._log("  [HITL] Action skipped by user.")
                        raw = self._session.chat(
                            f"The user declined to run '{tool_name}'. "
                            "Find an alternative approach or give the final_answer with the data you have.",
                            format="json"
                        )
                        continue

                result = self._execute_tool(tool_name, args)
                self._step_results.append({"tool": tool_name, "result": result})
                
                # Pillar 4A: Write results to Blackboard
                self._blackboard.log_step(tool_name, args, result)
                if "text" in result and isinstance(result["text"], str):
                    self._scraped_text = result["text"]
                    self._blackboard.write(Blackboard.SCRAPED_TEXT, result["text"])
                if "url" in result:
                    url_val = result["url"]
                    if url_val and url_val not in self._scraped_urls:
                        self._scraped_urls.append(url_val)
                    self._blackboard.write(Blackboard.SCRAPED_URL, url_val)

                context = _summarise_for_context(result)
                self._log(f"     Result preview: {context[:200]}...")

                feedback = (
                    f'Tool `{tool_name}` completed successfully.\n'
                    f'Result:\n{context}\n\n'
                    f'Now decide: call another tool or give a final_answer.'
                )
                raw = self._session.chat(feedback)
                continue

            # ── unknown action ─────────────────────────────────────────────────
            self._log(f"\n[step {step}] Unknown action '{action}', asking model to retry...")
            raw = self._session.chat(
                f"Unknown action '{action}'. "
                "You must respond with either a call_tool or final_answer JSON."
            )

        return (
            "⚠ Orchestrator reached the maximum step limit without a final answer. "
            f"Completed {len(self._step_results)} tool calls. "
            "Try rephrasing your request."
        )

    # ── Internal helpers ───────────────────────────────────────────────────────

    def _parse_decision(self, text: str) -> dict | None:
        """Parse the LLM's JSON response into a decision dict."""
        try:
            return extract_json(text)
        except ValueError:
            return None

    def _execute_tool(self, tool_name: str, args: dict) -> dict:
        """
        Substitute special variables in args, then call the agent.
        Returns the tool result dict (or an error dict on failure).
        """
        # Resolve $scraped_text placeholder
        resolved_args: dict[str, Any] = {}
        for k, v in args.items():
            if isinstance(v, str) and v.strip() == "$scraped_text":
                resolved_args[k] = self._scraped_text or "(no scraped text available)"
            else:
                resolved_args[k] = v

        try:
            entry = agents.REGISTRY.get(tool_name)
            if entry is None:
                available = ", ".join(agents.list_agents())
                return {
                    "error": f"No agent named '{tool_name}'. Available: {available}"
                }
            return entry["fn"](**resolved_args)
        except TypeError as e:
            return {"error": f"Wrong arguments for '{tool_name}': {e}"}
        except Exception as e:
            return {"error": f"'{tool_name}' raised an exception: {type(e).__name__}: {e}"}

    def _fmt_args(self, args: dict) -> str:
        """Format args for logging, truncating long text values."""
        parts = []
        for k, v in args.items():
            if isinstance(v, str) and len(v) > 60:
                parts.append(f'{k}="{v[:60]}..."')
            else:
                parts.append(f'{k}="{v}"')
        return ", ".join(parts)

    def _log(self, msg: str):
        if self.verbose:
            print(msg)

    # ── Step result access ─────────────────────────────────────────────────────

    def get_step_results(self) -> list[dict]:
        """Return the full (un-truncated) results of all tool calls."""
        return list(self._step_results)

    def get_scraped_text(self) -> str:
        """Return the most recently scraped plain text."""
        return self._scraped_text
