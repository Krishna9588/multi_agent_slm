"""
health_check.py -- Full System Diagnostic
------------------------------------------
Tests every subsystem of the Multi-Agent LLM system without requiring user input.
Prints a structured status report at the end.

Run: python health_check.py
"""

import sys
import os
import json
import time
import traceback

# Force UTF-8 output on Windows so box characters render
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Make sure we run from project root
os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.abspath(".."))

# ── ANSI colours ──────────────────────────────────────────────────────────────
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

OK   = f"{GREEN}[OK]{RESET}"
FAIL = f"{RED}[FAIL]{RESET}"
WARN = f"{YELLOW}[WARN]{RESET}"
SKIP = f"{YELLOW}[SKIP]{RESET}"

results = []   # list of (section, name, status, detail)

def record(section, name, status, detail=""):
    results.append((section, name, status, detail))
    icon = OK if status == "OK" else (FAIL if status == "FAIL" else (WARN if status == "WARN" else SKIP))
    print(f"  {icon}  {name:<40} {detail}")

def section(title):
    print(f"\n{BOLD}{CYAN}" + "-"*60 + f"{RESET}")
    print(f"{BOLD}{CYAN}  {title}{RESET}")
    print(f"{BOLD}{CYAN}" + "-"*60 + f"{RESET}")

# ══════════════════════════════════════════════════════════════════════════════
# 1. DEPENDENCY CHECK
# ══════════════════════════════════════════════════════════════════════════════
section("1. Python Dependencies")

REQUIRED_PKGS = [
    ("dotenv",              "python-dotenv"),
    ("requests",            "requests"),
    ("bs4",                 "beautifulsoup4"),
    ("duckduckgo_search",   "duckduckgo-search"),
    ("wikipedia",           "wikipedia"),
    ("arxiv",               "arxiv"),
    ("parsel",              "parsel"),
    ("trafilatura",         "trafilatura"),
]

OPTIONAL_PKGS = [
    ("playwright",          "playwright"),
    ("selenium",            "selenium"),
    ("chromadb",            "chromadb"),
    ("sentence_transformers","sentence-transformers"),
    ("instructor",          "instructor"),
]

for mod, pkg in REQUIRED_PKGS:
    try:
        __import__(mod)
        record("deps", pkg, "OK")
    except ImportError as e:
        record("deps", pkg, "FAIL", f"pip install {pkg}")

for mod, pkg in OPTIONAL_PKGS:
    try:
        __import__(mod)
        record("deps", pkg, "OK", "(optional)")
    except ImportError:
        record("deps", pkg, "SKIP", "optional — not installed")

# ══════════════════════════════════════════════════════════════════════════════
# 2. ENVIRONMENT / CONFIG
# ══════════════════════════════════════════════════════════════════════════════
section("2. Environment & Config")

from dotenv import load_dotenv
load_dotenv()

gemini_key = os.environ.get("GEMINI_API_KEY", "")
if gemini_key and gemini_key != "your_gemini_api_key_here":
    record("env", "GEMINI_API_KEY", "OK", f"set ({gemini_key[:8]}...)")
else:
    record("env", "GEMINI_API_KEY", "WARN", "not set — Gemini backend unavailable")

# DEFAULT_MODEL
try:
    from core.models import DEFAULT_MODEL
    record("env", "DEFAULT_MODEL", "OK", DEFAULT_MODEL)
except Exception as e:
    record("env", "DEFAULT_MODEL", "FAIL", str(e))

# ══════════════════════════════════════════════════════════════════════════════
# 3. OLLAMA CONNECTIVITY
# ══════════════════════════════════════════════════════════════════════════════
section("3. Ollama Server Connectivity")

import urllib.request, urllib.error

OLLAMA_URL = "http://localhost:11434"
ollama_alive = False

try:
    with urllib.request.urlopen(f"{OLLAMA_URL}/api/tags", timeout=5) as resp:
        tags_data = json.loads(resp.read())
        models = [m["name"] for m in tags_data.get("models", [])]
        record("ollama", "Ollama server reachable", "OK", f"{OLLAMA_URL}")
        record("ollama", "Installed models", "OK", ", ".join(models) if models else "(none)")
        ollama_alive = True
        # Check default model
        if DEFAULT_MODEL in models or any(DEFAULT_MODEL in m for m in models):
            record("ollama", f"Default model '{DEFAULT_MODEL}'", "OK", "loaded")
        else:
            record("ollama", f"Default model '{DEFAULT_MODEL}'", "WARN",
                   f"not found — available: {models[:3]}")
except Exception as e:
    record("ollama", "Ollama server reachable", "FAIL", str(e))

# ══════════════════════════════════════════════════════════════════════════════
# 4. LLM SESSION (basic chat round-trip)
# ══════════════════════════════════════════════════════════════════════════════
section("4. LLM Session Round-trip")

llm_ok = False
if ollama_alive:
    try:
        from core.models import get_conversation_session, DEFAULT_MODEL
        session = get_conversation_session(model=DEFAULT_MODEL)
        t0 = time.time()
        reply = session.chat("Reply with only the word PONG and nothing else.", format="json")
        elapsed = time.time() - t0
        if reply:
            record("llm", "Ollama chat round-trip", "OK", f"{elapsed:.1f}s — reply: {reply[:60]!r}")
            llm_ok = True
        else:
            record("llm", "Ollama chat round-trip", "FAIL", "Empty reply")
    except Exception as e:
        record("llm", "Ollama chat round-trip", "FAIL", str(e)[:120])
else:
    record("llm", "Ollama chat round-trip", "SKIP", "Ollama not reachable")

# ══════════════════════════════════════════════════════════════════════════════
# 5. AGENT REGISTRY AUTO-DISCOVERY
# ══════════════════════════════════════════════════════════════════════════════
section("5. Agent Registry Auto-Discovery")

EXPECTED_AGENTS = [
    "web_scraper", "link_extractor", "search_agent",
    "ner_agent", "sentiment_analysis", "page_classifier",
    "topic_modeling", "data_exporter_agent",
]

try:
    import agents
    registered = agents.list_agents()
    record("registry", "agents module import", "OK", f"{len(registered)} agents found")
    for name in EXPECTED_AGENTS:
        if name in registered:
            record("registry", f"  {name}", "OK")
        else:
            record("registry", f"  {name}", "FAIL", "missing from registry")
    # Any extra / unexpected agents
    extra = [a for a in registered if a not in EXPECTED_AGENTS]
    if extra:
        record("registry", "  Extra agents", "OK", ", ".join(extra))
except Exception as e:
    record("registry", "agents module import", "FAIL", traceback.format_exc()[:300])

# ══════════════════════════════════════════════════════════════════════════════
# 6. WEB SCRAPER — static page
# ══════════════════════════════════════════════════════════════════════════════
section("6. Web Scraper Agent")

try:
    from agents.web_scraper import web_scraper
    t0 = time.time()
    res = web_scraper("https://example.com", strategy="auto")
    elapsed = time.time() - t0
    if res.get("error") and res.get("word_count", 0) == 0:
        record("scraper", "web_scraper(example.com)", "FAIL", res["error"][:100])
    else:
        wc = res.get("word_count", 0)
        strat = res.get("strategy", "?")
        record("scraper", "web_scraper(example.com)", "OK",
               f"{wc} words via {strat} in {elapsed:.1f}s")
        if res.get("error"):
            record("scraper", "  (partial warning)", "WARN", res["error"][:80])
except Exception as e:
    record("scraper", "web_scraper(example.com)", "FAIL", str(e)[:120])

# ══════════════════════════════════════════════════════════════════════════════
# 7. LINK EXTRACTOR
# ══════════════════════════════════════════════════════════════════════════════
section("7. Link Extractor Agent")

try:
    from agents.link_extractor import link_extractor
    t0 = time.time()
    res = link_extractor("https://example.com")
    elapsed = time.time() - t0
    if res.get("error"):
        record("links", "link_extractor(example.com)", "FAIL", res["error"][:100])
    else:
        count = len(res.get("links", []))
        record("links", "link_extractor(example.com)", "OK",
               f"{count} links in {elapsed:.1f}s")
except Exception as e:
    record("links", "link_extractor(example.com)", "FAIL", str(e)[:120])

# ══════════════════════════════════════════════════════════════════════════════
# 8. SEARCH AGENT (all backends)
# ══════════════════════════════════════════════════════════════════════════════
section("8. Search Agent")

search_backends = [
    ("duckduckgo", "AI agent python"),
    ("wikipedia",  "who is Alan Turing"),
    ("arxiv",      "transformer attention mechanism paper"),
]

for backend, query in search_backends:
    try:
        from agents.search_agent import search_agent
        t0 = time.time()
        res = search_agent(query, backend=backend)
        elapsed = time.time() - t0
        if res.get("error"):
            record("search", f"search_agent({backend})", "WARN", res["error"][:80])
        else:
            total = res.get("total", 0)
            record("search", f"search_agent({backend})", "OK",
                   f"{total} results in {elapsed:.1f}s")
    except Exception as e:
        record("search", f"search_agent({backend})", "FAIL", str(e)[:100])

# ══════════════════════════════════════════════════════════════════════════════
# 9. LLM ANALYSIS AGENTS (using dummy text)
# ══════════════════════════════════════════════════════════════════════════════
section("9. LLM Analysis Agents (dummy text)")

DUMMY_TEXT = """
TechCorp Inc, headquartered in San Francisco, California, was founded by 
Dr. Alice Chen and Bob Martinez in 2018. They build innovative AI-powered 
data analytics platforms using Python, TensorFlow, and Google Cloud. Their 
flagship product, DataSight Pro, helps enterprises in New York and London 
unlock insights from complex datasets. The company recently partnered with 
Microsoft to integrate their technology into Azure AI services.
"""

if llm_ok:
    # NER Agent
    try:
        from agents.ner_agent import ner_agent
        t0 = time.time()
        res = ner_agent(DUMMY_TEXT)
        elapsed = time.time() - t0
        if res.get("error"):
            record("llm_agents", "ner_agent", "FAIL", res["error"][:100])
        else:
            people = len(res.get("people", []))
            orgs   = len(res.get("organizations", []))
            record("llm_agents", "ner_agent", "OK",
                   f"{people} people, {orgs} orgs in {elapsed:.1f}s")
    except Exception as e:
        record("llm_agents", "ner_agent", "FAIL", str(e)[:100])

    # Sentiment Analysis
    try:
        from agents.sentiment_analysis import sentiment_analysis
        t0 = time.time()
        res = sentiment_analysis(DUMMY_TEXT)
        elapsed = time.time() - t0
        if res.get("error"):
            record("llm_agents", "sentiment_analysis", "FAIL", res["error"][:100])
        else:
            sentiment = res.get("overall_sentiment", "?")
            record("llm_agents", "sentiment_analysis", "OK",
                   f"sentiment={sentiment} in {elapsed:.1f}s")
    except Exception as e:
        record("llm_agents", "sentiment_analysis", "FAIL", str(e)[:100])

    # Page Classifier
    try:
        from agents.page_classifier import page_classifier
        t0 = time.time()
        res = page_classifier(DUMMY_TEXT)
        elapsed = time.time() - t0
        if res.get("error"):
            record("llm_agents", "page_classifier", "FAIL", res["error"][:100])
        else:
            page_type = res.get("page_type", "?")
            record("llm_agents", "page_classifier", "OK",
                   f"type={page_type} in {elapsed:.1f}s")
    except Exception as e:
        record("llm_agents", "page_classifier", "FAIL", str(e)[:100])

    # Topic Modeling
    try:
        from agents.topic_modeling import topic_modeling
        t0 = time.time()
        res = topic_modeling(DUMMY_TEXT)
        elapsed = time.time() - t0
        if res.get("error"):
            record("llm_agents", "topic_modeling", "FAIL", res["error"][:100])
        else:
            topics = res.get("topics", [])
            record("llm_agents", "topic_modeling", "OK",
                   f"{len(topics)} topics in {elapsed:.1f}s — {topics[:3]}")
    except Exception as e:
        record("llm_agents", "topic_modeling", "FAIL", str(e)[:100])

else:
    for name in ["ner_agent", "sentiment_analysis", "page_classifier", "topic_modeling"]:
        record("llm_agents", name, "SKIP", "LLM not reachable")

# ══════════════════════════════════════════════════════════════════════════════
# 10. DATA EXPORTER AGENT
# ══════════════════════════════════════════════════════════════════════════════
section("10. Data Exporter Agent")

try:
    from agents.data_exporter_agent import data_exporter_agent

    dummy_data = json.dumps([
        {"name": "Alice Chen",   "role": "Founder & CEO",      "company": "TechCorp"},
        {"name": "Bob Martinez", "role": "Co-Founder & CTO",   "company": "TechCorp"},
        {"name": "Carol Singh",  "role": "VP Engineering",      "company": "TechCorp"},
    ])

    res = data_exporter_agent(dummy_data, filename_prefix="health_check_test")
    if res.get("error"):
        record("exporter", "data_exporter_agent", "FAIL", res["error"])
    else:
        fp = res.get("file_path", "?")
        record("exporter", "data_exporter_agent", "OK",
               f"wrote {res.get('message','?')} → {os.path.basename(fp)}")
except Exception as e:
    record("exporter", "data_exporter_agent", "FAIL", str(e)[:120])

# ══════════════════════════════════════════════════════════════════════════════
# 11. MEMORY SYSTEM
# ══════════════════════════════════════════════════════════════════════════════
section("11. Memory System")

try:
    from memory.memory_store import save_session, recall_similar, memory_backend
    backend = memory_backend()
    record("memory", "memory_backend detected", "OK", backend)

    # Save a dummy session
    save_session(
        task="health check: test memory store",
        answer="This is a diagnostic test session saved by health_check.py",
        urls=["https://example.com"]
    )
    record("memory", "save_session (long-term)", "OK")

    # Recall
    hits = recall_similar("memory store test", top_k=2)
    record("memory", "recall_similar", "OK", f"{len(hits)} hit(s) returned")

except Exception as e:
    record("memory", "memory system", "FAIL", str(e)[:120])

try:
    from memory.blackboard import Blackboard
    bb = Blackboard()
    bb.write("test_key", "test_value")
    assert bb.read("test_key") == "test_value", "Read mismatch"
    bb.log_step("test_tool", {"arg": "val"}, {"result": "ok"})
    bb.clear()
    assert bb.read("test_key") is None, "Clear failed"
    record("memory", "Blackboard (in-session)", "OK")
except Exception as e:
    record("memory", "Blackboard (in-session)", "FAIL", str(e)[:100])

# ══════════════════════════════════════════════════════════════════════════════
# 12. ORCHESTRATOR IMPORT & SYSTEM PROMPT BUILD
# ══════════════════════════════════════════════════════════════════════════════
section("12. Orchestrator Bootstrap")

try:
    from core.orchestrator import Orchestrator, _build_system_prompt
    prompt = _build_system_prompt()
    record("orchestrator", "System prompt build", "OK", f"{len(prompt.split())} words")

    orc = Orchestrator(verbose=False)
    record("orchestrator", "Orchestrator.__init__", "OK")
except Exception as e:
    record("orchestrator", "Orchestrator bootstrap", "FAIL", traceback.format_exc()[:300])

# ══════════════════════════════════════════════════════════════════════════════
# 13. END-TO-END ORCHESTRATOR RUN (mini task, no user input needed)
# ══════════════════════════════════════════════════════════════════════════════
section("13. End-to-End Orchestrator Run (mini task)")

if llm_ok:
    try:
        orc_e2e = Orchestrator(verbose=False)
        t0 = time.time()
        answer = orc_e2e.run(
            "Search for 'Python multi-agent systems' using duckduckgo and give me a one-sentence summary."
        )
        elapsed = time.time() - t0
        steps = orc_e2e.get_step_results()
        if answer and "⚠" not in answer:
            record("e2e", "Orchestrator mini task", "OK",
                   f"{len(steps)} tool call(s) in {elapsed:.1f}s")
        else:
            record("e2e", "Orchestrator mini task", "WARN",
                   f"answer may be incomplete: {answer[:80]!r}")
    except Exception as e:
        record("e2e", "Orchestrator mini task", "FAIL", str(e)[:150])
else:
    record("e2e", "Orchestrator mini task", "SKIP", "LLM not reachable")

# ══════════════════════════════════════════════════════════════════════════════
# FINAL REPORT
# ══════════════════════════════════════════════════════════════════════════════
print(f"\n\n{BOLD}" + "="*60)
print("  HEALTH REPORT SUMMARY")
print("="*60 + f"{RESET}\n")

ok_count   = sum(1 for r in results if r[2] == "OK")
fail_count = sum(1 for r in results if r[2] == "FAIL")
warn_count = sum(1 for r in results if r[2] == "WARN")
skip_count = sum(1 for r in results if r[2] == "SKIP")
total      = len(results)

# Print failures and warnings first
if fail_count:
    print(f"{BOLD}{RED}  FAILURES ({fail_count}):{RESET}")
    for section_name, name, status, detail in results:
        if status == "FAIL":
            print(f"    • [{section_name}] {name}: {detail}")

if warn_count:
    print(f"\n{BOLD}{YELLOW}  WARNINGS ({warn_count}):{RESET}")
    for section_name, name, status, detail in results:
        if status == "WARN":
            print(f"    • [{section_name}] {name}: {detail}")

if skip_count:
    print(f"\n{BOLD}{YELLOW}  SKIPPED ({skip_count}):{RESET}")
    for section_name, name, status, detail in results:
        if status == "SKIP":
            print(f"    • [{section_name}] {name}: {detail}")

print(f"\n{BOLD}  Score: {ok_count}/{total} checks passed  "
      f"({fail_count} failed, {warn_count} warnings, {skip_count} skipped){RESET}")

if fail_count == 0 and warn_count == 0:
    print(f"\n{GREEN}{BOLD}  ALL SYSTEMS OPERATIONAL{RESET}")
elif fail_count == 0:
    print(f"\n{YELLOW}{BOLD}  SYSTEM FUNCTIONAL WITH WARNINGS{RESET}")
else:
    print(f"\n{RED}{BOLD}  SYSTEM HAS FAILURES — see above{RESET}")

print()
