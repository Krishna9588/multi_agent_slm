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
import uuid
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import agents
from agents._base import extract_json
from core.models import get_conversation_session, DEFAULT_MODEL
from memory import Blackboard, save_session, recall_similar, memory_backend
from agents._base import extract_json

# ── Config ─────────────────────────────────────────────────────────────────────

MAX_STEPS     = 20      # max ReAct iterations (prevents infinite loops)
CONTEXT_LIMIT = 800     # max words of a tool result echoed back to the LLM

# Pillar 5: Tools that require human confirmation before execution
HITL_TOOLS = ["data_exporter_agent"]

# ── System prompt builder ──────────────────────────────────────────────────────

def _build_system_prompt(active_tools: list[str] = None) -> str:
    """
    Dynamically builds the orchestrator's system prompt from the agent REGISTRY.
    Only includes the tools specified in active_tools to reduce cognitive load.
    """
    tool_lines: list[str] = []
    for name, entry in sorted(agents.REGISTRY.items()):
        if active_tools and name not in active_tools:
            continue
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

    return f"""You are an intelligent task orchestrator.

AVAILABLE TOOLS:
{tools_block}

STRICT RULES:
1. JSON ONLY. No markdown, no conversational text.
2. TO CALL A TOOL: {{"action": "call_tool", "tool": "<tool_name>", "args": {{<args>}}}}
3. TO FINISH: {{"action": "final_answer", "answer": "<your complete, detailed answer>"}}
4. Re-use scraped text by passing {{"text": "$scraped_text"}} to text-analysis tools.
5. DEEP RESEARCH: For multi-page profiling, you MUST use `deep_research_agent`. For exporting data, you MUST use `data_exporter_agent` and ask the user for permission first.
"""

def _simplify_prompt(user_task: str, model: str) -> str:
    """
    Pre-processes complex prompts into structured, actionable step-by-step plans.
    Prevents the ReAct loop from getting lost or hallucinating syntax on complex tasks.
    """
    prompt = f"""You are a prompt engineer for an AI agent system.
The user has provided a complex request:
"{user_task}"

Rewrite this request into a clear, step-by-step instruction plan that a ReAct AI agent can execute.
Keep it concise, actionable, and remove any ambiguity. 
Do NOT answer the prompt yourself, just output the rewritten step-by-step instructions."""
    try:
        session = get_conversation_session(model=model, system_prompt="You rewrite complex prompts into clear step-by-step instructions. Output ONLY the rewritten prompt.")
        response = session.chat(prompt)
        return response.strip()
    except Exception:
        return user_task

def _select_tools(user_task: str, model: str) -> list[str]:
    """
    Pre-processes the user task to select only the most relevant tools.
    Dramatically reduces cognitive load on 8B models.
    """
    available_tools = ", ".join(sorted(agents.REGISTRY.keys()))
    prompt = f"""You are a tool selector. 
User Task: "{user_task}"
Available Tools: {available_tools}
Pick up to 4 tools needed to solve this. Respond with ONLY a JSON list of strings, e.g. ["web_scraper", "ner_agent"]."""

    try:
        session = get_conversation_session(model=model, system_prompt="You only output JSON lists of strings. Do not use markdown backticks.")
        response = session.chat(prompt)
        
        # Quick cleanup in case it still uses markdown backticks
        response = response.strip()
        if response.startswith("```"):
            import re
            m = re.search(r"```(?:json)?\s*(\[[\s\S]+?\])\s*```", response)
            if m:
                response = m.group(1)
                
        tools = json.loads(response)
        if isinstance(tools, list):
            # Always ensure web_scraper is available if deep_research isn't selected just in case
            if "deep_research_agent" not in tools and "web_scraper" not in tools:
                tools.append("web_scraper")
            return [t for t in tools if t in agents.REGISTRY]
    except Exception:
        pass
    return list(agents.REGISTRY.keys())  # fallback to all tools if parsing fails


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
        self._session = get_conversation_session(model=self.model)

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

        # Pillar X: Prompt Simplifier for complex queries
        if len(user_task.split()) > 15:
            self._log(f"  [Prompt Pre-Processor] Analyzing complex task...")
            structured_task = _simplify_prompt(user_task, self.model)
            self._log(f"  [Prompt Pre-Processor] Rewritten Task:\n{structured_task}")
            user_task = f"Original Request: {user_task}\n\nStructured Execution Plan:\n{structured_task}"

        active_tools = _select_tools(user_task, self.model)
        self._log(f"  [Tool Selector] Active tools: {', '.join(active_tools)}")

        self._session.set_system_prompt(_build_system_prompt(active_tools))

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
        raw = self._session.chat(f"User task: {user_task}{memory_context}")

        for step in range(1, MAX_STEPS + 1):
            decision = self._parse_decision(raw)

            if decision is None:
                self._log(f"\n[step {step}] Could not parse LLM response, asking it to retry...")
                self._log(f"    [DEBUG RAW OUTPUT]:\n{raw}\n{'-'*40}")
                raw = self._session.chat(
                    "Your response was not valid JSON. "
                    "Respond with ONLY a call_tool or final_answer JSON object."
                )
                continue

            action = decision.get("action")

            # ── final_answer ───────────────────────────────────────────────────
            if action == "final_answer":
                answer = decision.get("answer", "")
                if not answer or answer.strip() == "":
                    # Failsafe: if the LLM output an empty answer but we have a recent step result, return that.
                    if self._step_results:
                        answer = f"(Model returned empty answer, but here is the last retrieved data):\n{json.dumps(self._step_results[-1], indent=2)}"
                    else:
                        answer = "(no answer provided)"
                self._log(f"\n[step {step}] -> Final answer ready\n")
                # Pillar 4B: Persist session to long-term memory
                save_session(user_task, answer, self._scraped_urls)
                return answer

            # ── call_tool ──────────────────────────────────────────────────────
            if action == "call_tool":
                tool_name = decision.get("tool", "")
                args      = decision.get("args", {})

                self._log(f"\n[step {step}] -> Calling: {tool_name}({self._fmt_args(args)})")

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

                try:
                    result = self._execute_tool(tool_name, args)
                    self._step_results.append({"tool": tool_name, "result": result})
                    
                    # Prevent context overflow: intercept huge outputs
                    result_str = json.dumps(result, ensure_ascii=False)
                    if len(result_str) > 2000:
                        output_dir = os.path.join(os.getcwd(), "archive", "outputs")
                        os.makedirs(output_dir, exist_ok=True)
                        filepath = os.path.join(output_dir, f"tool_result_{uuid.uuid4().hex[:8]}.json")
                        with open(filepath, "w", encoding="utf-8") as f:
                            f.write(result_str)
                        result["_MEMORY_FILE"] = filepath
                        self._log(f"    (Tool output massive. Saved full data to {filepath})")
                        
                except Exception as e:
                    self._log(f"    Error: {e}")
                    raw = self._session.chat(
                        f"Tool execution failed: {e}\nProvide an alternative plan or final_answer."
                    )
                    continue
                
                # Dynamic Reloading for Meta Agent
                if tool_name == "meta_agent" and result.get("success"):
                    self._log("\n  [System] meta_agent created a new tool. Reloading agent registry...")
                    import importlib
                    importlib.reload(agents)
                    self._session.set_system_prompt(_build_system_prompt())
                    self._log(f"  [System] Registry reloaded successfully. Total tools: {len(agents.REGISTRY)}")
                
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
                
                # Append the memory file instruction if this result was massive
                if "_MEMORY_FILE" in result:
                    context += f"\n\n[SYSTEM WARNING]: The actual output was massive and has been safely saved to a local memory file: {result['_MEMORY_FILE']}\nDO NOT attempt to output the full data in your final_answer. Pass the filepath '{result['_MEMORY_FILE']}' as `source_file` to data_exporter_agent to export it."
                    
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
            "[WARNING] Orchestrator reached the maximum step limit without a final answer. "
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
