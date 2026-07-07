"""
run.py — Unified CLI Entry Point
--------------------------------
Start the system from the terminal. 
This script acts as the single point of contact for the entire architecture.

Usage:
    python run.py                                  # interactive autonomous mode (auto-routes)
    python run.py "analyse https://proplusdata.co" # autonomous one-shot task
    python run.py --premium                        # force cloud model (gemini) for complex tasks
    python run.py --chat                           # force basic chat (no tools)
    python run.py --council "your question"        # force multi-LLM council deliberation
    python run.py --list-agents                    # show all registered agents

Interactive commands:
    /auto     — switch to Autonomous Intent Router mode (default)
    /agents   — list all registered agents and their descriptions
    /save     — save last task's raw tool results to archive/results.json
    /reset    — start a fresh session
    /chat     — force basic conversational chat (no agents)
    /agent    — force agent orchestrator mode
    /council  — force Council of Models mode (multi-LLM debate)
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
    print("  Commands: /auto  /agents  /save  /reset  /chat  /agent  /council  /quit")
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


# ── Autonomous Intent Router ───────────────────────────────────────────────────

def _autonomous_route(task: str) -> str:
    """Uses a fast local model to classify the user's intent into an execution mode."""
    prompt = f"""You are an Autonomous Router for an AI Agent ecosystem.
The user has provided a request: "{task}"

Analyze the request and choose ONE of the following modes:
- COUNCIL: For philosophical debate, code review, high-stakes decisions requiring multiple perspectives.
- AGENT: For standard tool execution, web scraping, API calls, simple data extraction, complex research and reporting.
- CHAT: For simple conversational queries, greetings, or questions that don't need any tools.

Respond with ONLY ONE WORD from the list above. No markdown, no explanations."""
    try:
        session = get_conversation_session(model="llama3.1:8b", system_prompt="You only output a single word: COUNCIL, AGENT, or CHAT.")
        response = session.chat(prompt).strip().upper()
        # Strip potential markdown formatting if it misbehaves
        response = response.replace("`", "").strip()
        if response in ["COUNCIL", "AGENT", "CHAT"]:
            return response
    except Exception:
        pass
    return "AGENT"  # Default fallback


# ── One-shot mode ──────────────────────────────────────────────────────────────

def _run_one_shot(task: str):
    original_model = core.models.DEFAULT_MODEL
    orc = Orchestrator(model=core.models.DEFAULT_MODEL, verbose=True)
    try:
        answer = orc.run(task)
    except Exception as e:
        if ("429" in str(e) or "RESOURCE_EXHAUSTED" in str(e) or "All retries failed" in str(e)) and "gemini" in original_model.lower():
            print("\n  [Fallback] Premium API quota exhausted! Falling back to local model (llama3.1:8b)...")
            core.models.DEFAULT_MODEL = "llama3.1:8b"
            orc = Orchestrator(model=core.models.DEFAULT_MODEL, verbose=True)
            answer = orc.run(task)
        else:
            raise e
    finally:
        core.models.DEFAULT_MODEL = original_model
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
        elif task.lower() == "/council":
            mode = "COUNCIL"
            _banner(mode)
            continue
        elif task.lower() == "/auto":
            mode = "AUTO"
            _banner("AUTO (Intent Router)")
            continue

        # ── Execution ──────────────────────────────────────────────────────────
        try:
            print()
            current_mode = mode
            if current_mode == "AUTO":
                current_mode = _autonomous_route(task)
                print(f"  [Router] Automatically selected mode: {current_mode}\n")

            if current_mode == "PREMIUM":
                original_model = core.models.DEFAULT_MODEL
                core.models.DEFAULT_MODEL = "gemini-2.5-flash"
                try:
                    orc_prem = Orchestrator(model=core.models.DEFAULT_MODEL, verbose=True)
                    answer = orc_prem.run(task)
                    last_results = orc_prem.get_step_results()
                except Exception as e:
                    if ("429" in str(e) or "RESOURCE_EXHAUSTED" in str(e) or "All retries failed" in str(e)):
                        print("\n  [Fallback] Premium API quota exhausted! Falling back to local model (llama3.1:8b)...")
                        core.models.DEFAULT_MODEL = "llama3.1:8b"
                        orc_local = Orchestrator(model=core.models.DEFAULT_MODEL, verbose=True)
                        answer = orc_local.run(task)
                        last_results = orc_local.get_step_results()
                    else:
                        raise e
                finally:
                    core.models.DEFAULT_MODEL = original_model

                print("\n" + "-" * WIDTH)
                print("ANSWER:")
                print(answer)
                print("-" * WIDTH)
            elif current_mode == "AGENT":
                answer = orc.run(task)
                last_results = orc.get_step_results()
                print("\n" + "-" * WIDTH)
                print("ANSWER:")
                print(answer)
                print("-" * WIDTH)
            elif current_mode == "COUNCIL":
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
    args = sys.argv[1:]
    
    if "--premium" in args:
        core.models.DEFAULT_MODEL = "gemini-2.5-flash"
        args.remove("--premium")

    if not args:
        _run_interactive("AUTO")
    elif args[0] == "--chat":
        _run_interactive("CHAT")
    elif args[0] == "--council":
        if len(args) > 1:
            # One-shot council mode
            task_str = " ".join(args[1:])
            from core.council import Council
            print("\n" + "=" * WIDTH)
            print("  🏛️  COUNCIL OF MODELS — Deliberation Starting")
            print("=" * WIDTH + "\n")
            council = Council(verbose=True)
            result = council.deliberate(task_str)
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
            _run_interactive("COUNCIL")
    elif args[0] == "--list-agents":
        _print_agents()
    else:
        # Join all args as the one-shot task
        task_str = " ".join(args)
        route = _autonomous_route(task_str)
        print(f"  [Router] Automatically selected mode: {route}\n")
        if route == "PREMIUM":
            core.models.DEFAULT_MODEL = "gemini-2.5-flash"
            _run_one_shot(task_str)
        elif route == "COUNCIL":
            from core.council import Council
            print("\n" + "=" * WIDTH)
            print("  🏛️  COUNCIL OF MODELS — Deliberation Starting")
            print("=" * WIDTH + "\n")
            council = Council(verbose=True)
            result = council.deliberate(task_str)
            print("\n" + "=" * WIDTH)
            print("COUNCIL VERDICT:")
            print("=" * WIDTH)
            print(result["final_answer"])
            print("\n" + "-" * WIDTH)
            votes_str = ", ".join(f"{m}: {v}" for m, v in result["votes"].items())
            print(f"  Consensus: {'✅ YES' if result['consensus'] else '⚠️ NO'}")
            print(f"  Votes: {votes_str}")
            print("-" * WIDTH)
        elif route == "CHAT":
            chat_session = get_conversation_session(model=core.models.DEFAULT_MODEL)
            print("-" * WIDTH)
            print("Assistant: ", end="", flush=True)
            chat_session.chat(task_str, stream=True)
            print("\n" + "-" * WIDTH)
        else:
            _run_one_shot(task_str)
