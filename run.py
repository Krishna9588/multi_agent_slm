"""
run.py — Unified CLI Entry Point
--------------------------------
Start the system from the terminal. 
This script acts as the single point of contact for the entire architecture.

Usage:
    python run.py                                  # interactive agent mode
    python run.py --premium                        # use cloud model (gemini) for complex tasks
    python run.py --chat                           # interactive basic chat (no tools)
    python run.py --council "your question"         # multi-LLM council deliberation
    python run.py "analyse https://proplusdata.co" # one-shot task
    python run.py --list-agents                    # show all registered agents

Interactive commands:
    /agents   — list all registered agents and their descriptions
    /save     — save last task's raw tool results to archive/results.json
    /reset    — start a fresh session
    /chat     — switch to basic conversational chat (no agents)
    /agent    — switch to agent orchestrator mode
    /council  — switch to Council of Models mode (multi-LLM debate)
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
from core.lc_orchestrator import run_lc_agent

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
    print("  Commands: /agents  /save  /reset  /chat  /agent  /council  /quit")
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

def _run_one_shot(task: str, lc_mode: bool = True):
    if lc_mode:
        print(f"\n[Running via LangChain Agent: {core.models.DEFAULT_MODEL}]")
        answer = run_lc_agent(task)
    else:
        print(f"\n[Running via Custom Orchestrator: {core.models.DEFAULT_MODEL}]")
        orc = Orchestrator(model=core.models.DEFAULT_MODEL, verbose=True)
        answer = orc.run(task)

    print("\n" + "-" * WIDTH)
    print("ANSWER:")
    print(answer)
    print("-" * WIDTH)

    if not lc_mode:
        results = orc.get_step_results()
        if results:
            os.makedirs("archive", exist_ok=True)
            with open("archive/results.json", "w", encoding="utf-8") as f:
                json.dump({"task": task, "answer": answer, "tool_results": results}, f, indent=2, ensure_ascii=False)
            print(f"\n  Raw tool results saved -> archive/results.json")


# ── Interactive mode ───────────────────────────────────────────────────────────

def _run_interactive(start_mode="AGENT", lc_mode: bool = True):
    mode = start_mode
    _banner(mode)
    
    orc = None
    if not lc_mode:
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
            if mode == "AGENT" and not lc_mode and last_results:
                os.makedirs("archive", exist_ok=True)
                with open("archive/results.json", "w", encoding="utf-8") as f:
                    json.dump(last_results, f, indent=2, ensure_ascii=False)
                print("  [OK] Saved to archive/results.json")
            elif lc_mode:
                print("  /save is currently only supported in --mode react")
            else:
                print("  No agent results to save.")
            continue
        elif task.lower() == "/reset":
            if mode == "AGENT":
                if not lc_mode:
                    orc = Orchestrator(model=core.models.DEFAULT_MODEL, verbose=True)
                # For lc_mode, memory resets are handled per thread_id, we'd generate a new thread_id here if needed
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
        elif task.lower() == "/council":
            mode = "COUNCIL"
            _banner(mode)
            continue

        # ── Execution ──────────────────────────────────────────────────────────
        try:
            print()
            if mode == "AGENT":
                if lc_mode:
                    answer = run_lc_agent(task, thread_id="interactive_session")
                else:
                    answer = orc.run(task)
                    last_results = orc.get_step_results()
                print("\n" + "-" * WIDTH)
                print("ANSWER:")
                print(answer)
                print("-" * WIDTH)
            elif mode == "COUNCIL":
                from core.council import Council
                print("\n" + "=" * WIDTH)
                print("  🏛️  COUNCIL OF MODELS — Deliberation Starting")
                print("=" * WIDTH + "\n")
                council = Council(verbose=True)
                result = council.deliberate(task)
                print("\n" + "=" * WIDTH)
                print("COUNCIL VERDICT:")
                print("=" * WIDTH)
                print(result["final_answer"])
                print("\n" + "-" * WIDTH)
                votes_str = ", ".join(f"{m}: {v}" for m, v in result["votes"].items())
                print(f"  Consensus: {'✅ YES' if result['consensus'] else '⚠️ NO'}")
                print(f"  Votes: {votes_str}")
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
    import argparse
    parser = argparse.ArgumentParser(description="Unified AI System CLI")
    parser.add_argument("--premium", action="store_true", help="Use cloud model (gemini) for complex tasks")
    parser.add_argument("--chat", action="store_true", help="Interactive basic chat (no tools)")
    parser.add_argument("--list-agents", action="store_true", help="Show all registered agents")
    parser.add_argument("--mode", choices=["react", "lc"], default="lc", help="react=legacy custom loop, lc=LangChain agent (default)")
    parser.add_argument("task", nargs="*", help="One-shot task description")

    args = parser.parse_args()
    
    if args.premium:
        core.models.DEFAULT_MODEL = "gemini-2.5-flash"

    lc_mode = (args.mode == "lc")

    if args.list_agents:
        _print_agents()
    elif args.chat:
        _run_interactive("CHAT", lc_mode=lc_mode)
    elif args.task:
        task_str = " ".join(args.task)
        _run_one_shot(task_str, lc_mode=lc_mode)
    else:
        _run_interactive("AGENT", lc_mode=lc_mode)
