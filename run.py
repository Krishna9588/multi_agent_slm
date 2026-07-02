"""
run.py — Unified CLI Entry Point
--------------------------------
Start the system from the terminal. 
This script acts as the single point of contact for the entire architecture.

Usage:
    python run.py                                  # interactive agent mode
    python run.py --premium                        # use cloud model (gemini) for complex tasks
    python run.py --chat                           # interactive basic chat (no tools)
    python run.py "analyse https://proplusdata.co" # one-shot task
    python run.py --list-agents                    # show all registered agents

Interactive commands:
    /agents   — list all registered agents and their descriptions
    /save     — save last task's raw tool results to archive/results.json
    /reset    — start a fresh session
    /chat     — switch to basic conversational chat (no agents)
    /agent    — switch to agent orchestrator mode
    /quit     — exit
"""

import json
import sys
import os

if sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

from core.models import get_conversation_session
import core.models
from core.orchestrator import Orchestrator

# ── Banner ─────────────────────────────────────────────────────────────────────

WIDTH = 62

def _banner(mode="AGENT"):
    import agents
    print("=" * WIDTH)
    print("  Unified AI System".center(WIDTH))
    print(f"  Mode  : {mode}".center(WIDTH))
    print(f"  Model : {core.models.DEFAULT_MODEL}".center(WIDTH))
    if mode == "AGENT":
        print(f"  Agents: {', '.join(agents.list_agents())}".center(WIDTH))
    print("=" * WIDTH)
    print("  Type a message or task.")
    print("  Commands: /agents  /save  /reset  /chat  /agent  /quit")
    print("=" * WIDTH)


# ── Agent listing ──────────────────────────────────────────────────────────────

def _print_agents():
    import agents
    print(f"\n  {'-'*58}")
    print(f"  {'Registered Agents':^58}")
    print(f"  {'-'*58}")
    for name, entry in sorted(agents.REGISTRY.items()):
        desc = entry["description"]
        first_sentence = desc.split(".")[0].strip()
        print(f"\n  [{name}]")
        print(f"    {first_sentence}")
    print()


# ── One-shot mode ──────────────────────────────────────────────────────────────

def _run_one_shot(task: str):
    orc = Orchestrator(model=core.models.DEFAULT_MODEL, verbose=True)
    answer = orc.run(task)
    print("\n" + "-" * WIDTH)
    print("ANSWER:")
    print(answer)
    print("-" * WIDTH)

    results = orc.get_step_results()
    if results:
        os.makedirs("archive", exist_ok=True)
        with open("archive/results.json", "w", encoding="utf-8") as f:
            json.dump({"task": task, "answer": answer, "tool_results": results}, f, indent=2, ensure_ascii=False)
        print(f"\n  Raw tool results saved -> archive/results.json")


# ── Interactive mode ───────────────────────────────────────────────────────────

def _run_interactive(start_mode="AGENT"):
    mode = start_mode
    _banner(mode)
    
    orc = Orchestrator(model=core.models.DEFAULT_MODEL, verbose=True)
    chat_session = get_conversation_session(model=core.models.DEFAULT_MODEL)
    last_results = []

    while True:
        try:
            task = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting.")
            break

        if not task:
            continue

        # ── Commands ───────────────────────────────────────────────────────────
        if task.lower() == "/quit":
            print("Goodbye!")
            break
        elif task.lower() == "/agents":
            _print_agents()
            continue
        elif task.lower() == "/save":
            if mode == "AGENT" and last_results:
                os.makedirs("archive", exist_ok=True)
                with open("archive/results.json", "w", encoding="utf-8") as f:
                    json.dump(last_results, f, indent=2, ensure_ascii=False)
                print("  [OK] Saved to archive/results.json")
            else:
                print("  No agent results to save.")
            continue
        elif task.lower() == "/reset":
            if mode == "AGENT":
                orc = Orchestrator(model=core.models.DEFAULT_MODEL, verbose=True)
            else:
                chat_session.reset()
            last_results = []
            print(f"  [OK] {mode} session reset.")
            continue
        elif task.lower() == "/chat":
            mode = "CHAT"
            _banner(mode)
            continue
        elif task.lower() == "/agent":
            mode = "AGENT"
            _banner(mode)
            continue

        # ── Execution ──────────────────────────────────────────────────────────
        try:
            print()
            if mode == "AGENT":
                answer = orc.run(task)
                last_results = orc.get_step_results()
                print("\n" + "-" * WIDTH)
                print("ANSWER:")
                print(answer)
                print("-" * WIDTH)
            else:
                print("-" * WIDTH)
                print("Assistant: ", end="", flush=True)
                # Stream the chat
                chat_session.chat(task, stream=True)
                print("-" * WIDTH)
                
        except Exception as e:
            print(f"\n[ERROR] {type(e).__name__}: {e}")
            print("  Check model connection (Ollama running / Gemini API Key set).")


# ── Entry point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    args = sys.argv[1:]
    
    if "--premium" in args:
        core.models.DEFAULT_MODEL = "gemini-2.5-flash"
        args.remove("--premium")

    if not args:
        _run_interactive("AGENT")
    elif args[0] == "--chat":
        _run_interactive("CHAT")
    elif args[0] == "--list-agents":
        _print_agents()
    else:
        # Join all args as the one-shot task
        task_str = " ".join(args)
        _run_one_shot(task_str)
