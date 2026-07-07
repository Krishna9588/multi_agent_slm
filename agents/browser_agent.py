"""
Agent: browser_agent — The Browser Autopilot
---------------------------------------------
A Playwright-powered stateful browser automation agent.
Accepts natural-language TASK instructions and autonomously executes
multi-step browser interactions (click, type, navigate, iterate, extract).

Architecture:
    The Orchestrator calls browser_agent(url, task) ONCE.
    Internally, browser_agent runs its OWN ReAct loop:
        1. Navigate to URL
        2. Read the accessibility tree (interactive elements + page text)
        3. Ask the LLM: "Given this page state and the task, what should I do next?"
        4. LLM responds with: click(id), type(id, text), scroll(), extract(), navigate(url), or done(data)
        5. Execute the action, read the new page state, loop back to step 3
        6. When done, return the collected data to the Orchestrator

This replaces the old Swarm-based handoff which couldn't handle multi-step tasks.
"""

import os
import json
import time
import re
from urllib.parse import urlparse

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright = None

from agents._base import extract_json

# ── Constants ──────────────────────────────────────────────────────────────────

MAX_BROWSER_STEPS = 50  # Max actions before the autopilot gives up
PAGE_TEXT_LIMIT = 4000  # Max chars of page text sent to LLM per step
ELEMENT_LIMIT = 80       # Max interactive elements sent to LLM per step
AUTOSAVE_DIR = os.path.join(os.getcwd(), "archive", "outputs", "autopilot_recovery")


# ── Browser Session (Singleton) ───────────────────────────────────────────────

class BrowserSession:
    """A persistent Playwright browser session with Secure Vault integration."""

    def __init__(self):
        if sync_playwright is None:
            raise ImportError("Playwright is not installed. Run: pip install playwright && playwright install")
        self._p = sync_playwright().start()
        
        # ── Isolation Route 1: Local Docker Sandbox ──
        try:
            print("  [Browser] 🐳 Attempting connection to local Docker sandbox (ws://localhost:3000)...")
            self.browser = self._p.chromium.connect_over_cdp("ws://localhost:3000")
            print("  [Browser] ✅ Connected to Docker sandbox.")
        except Exception:
            print("  [Browser] ⚠️ Docker sandbox unreachable. Attempting to start it automatically...")
            import subprocess
            try:
                subprocess.run(
                    ["docker-compose", "up", "-d", "browser-sandbox"], 
                    cwd=os.getcwd(), 
                    check=True, 
                    capture_output=True
                )
                print("  [Browser] 🐳 Docker container started. Waiting for WebSocket to boot...")
                time.sleep(3)
                self.browser = self._p.chromium.connect_over_cdp("ws://localhost:3000")
                print("  [Browser] ✅ Connected to Docker sandbox.")
            except Exception as docker_err:
                print(f"  [Browser] ⚠️ Could not start or connect to Docker sandbox: {docker_err}")
                
                # ── Isolation Route 2: E2B Cloud Sandbox Fallback ──
            e2b_api_key = os.getenv("E2B_API_KEY")
            if not e2b_api_key:
                raise RuntimeError(
                    "❌ ISOLATION FAILED: Could not connect to local Docker sandbox (ws://localhost:3000), "
                    "and E2B_API_KEY is not set in .env for cloud fallback.\n"
                    "Please either run `docker-compose up -d browser-sandbox` or add E2B_API_KEY to your .env file."
                )
            
            print("  [Browser] ☁️ Attempting E2B Cloud Sandbox fallback...")
            try:
                from e2b import Sandbox
            except ImportError:
                raise ImportError("e2b package is not installed. Please run: pip install e2b>=0.14.0")
                
            try:
                # E2B Sandbox setup
                self.sandbox = Sandbox.create()
                print("  [Browser] ☁️ Setting up Playwright in E2B (this takes ~1 min on cold start)...")
                
                # Install Python, Playwright, Chromium inside sandbox
                setup_cmd = (
                    "sudo apt update && sudo apt install -y python3-pip && "
                    "pip3 install playwright && playwright install --with-deps chromium"
                )
                self.sandbox.commands.run(setup_cmd)
                
                # Launch CDP Server bound to 0.0.0.0 so we can access it over the internet
                print("  [Browser] ☁️ Launching Playwright CDP server...")
                py_script = (
                    "from playwright.sync_api import sync_playwright; "
                    "import time; "
                    "p = sync_playwright().start(); "
                    "server = p.chromium.launch_server(port=9222, host='0.0.0.0'); "
                    "print('Server running...'); "
                    "time.sleep(3600)"
                )
                self.sandbox.commands.run(f"python3 -c \"{py_script}\"", background=True)
                time.sleep(5)  # Give the server time to start
                
                ws_url = f"ws://{self.sandbox.get_host(9222)}"
                print(f"  [Browser] ☁️ Connecting to E2B CDP at {ws_url}...")
                self.browser = self._p.chromium.connect_over_cdp(ws_url)
                print("  [Browser] ✅ Connected to E2B cloud sandbox.")
            except Exception as e2b_err:
                raise RuntimeError(f"Isolation failed. Docker unreachable, and E2B fallback failed: {str(e2b_err)}")
        self.context = self.browser.new_context(
            viewport={"width": 1280, "height": 900},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        self.page = self.context.new_page()
        self._loaded_sessions = set()
        self._vault = None

        try:
            from core.secure_vault import SecureVault
            self._vault = SecureVault()
        except Exception:
            pass

    def _inject_session(self, url: str):
        """Auto-inject encrypted session cookies for the domain if available."""
        domain = urlparse(url).netloc.replace("www.", "").split('.')[0]
        if self._vault and domain not in self._loaded_sessions:
            if self._vault.is_session_valid(domain):
                print(f"  [Browser] 🔓 Decrypting session for '{domain}'...")
                temp_file = self._vault.export_decrypted_temp(domain)
                if temp_file:
                    try:
                        self.page.close()
                        self.context.close()
                        self.context = self.browser.new_context(storage_state=temp_file)
                        self.page = self.context.new_page()
                        self._loaded_sessions.add(domain)
                        print(f"  [Browser] 🟢 Session injected for '{domain}'.")
                    finally:
                        self._vault.cleanup_temp(domain)

    def goto(self, url: str, wait: str = "networkidle"):
        """Navigate to a URL with auto-session injection."""
        self._inject_session(url)
        try:
            self.page.goto(url, wait_until=wait, timeout=30000)
        except Exception:
            # Fallback: some pages never reach networkidle
            try:
                self.page.goto(url, wait_until="domcontentloaded", timeout=30000)
            except Exception as e:
                return f"Navigation failed: {str(e)}"
        time.sleep(1)  # Brief settle time for JS rendering
        return f"Navigated to {url}"

    def click(self, element_id: int):
        """Click an element by its data-agent-id."""
        selector = f"[data-agent-id='{element_id}']"
        try:
            self.page.click(selector, timeout=5000)
            time.sleep(1.5)
            return f"Clicked element {element_id}"
        except Exception as e:
            return f"Click failed on element {element_id}: {str(e)}"

    def type_text(self, element_id: int, text: str):
        """Type text into an input by its data-agent-id."""
        selector = f"[data-agent-id='{element_id}']"
        try:
            self.page.fill(selector, text, timeout=5000)
            time.sleep(0.5)
            return f"Typed '{text}' into element {element_id}"
        except Exception as e:
            return f"Type failed on element {element_id}: {str(e)}"

    def scroll_down(self):
        """Scroll down one viewport height."""
        self.page.evaluate("window.scrollBy(0, window.innerHeight)")
        time.sleep(1)
        return "Scrolled down one page"

    def go_back(self):
        """Navigate back in browser history."""
        try:
            self.page.go_back(wait_until="domcontentloaded", timeout=15000)
            time.sleep(1)
            return "Navigated back"
        except Exception as e:
            return f"Go back failed: {str(e)}"

    def get_page_state(self) -> dict:
        """
        Extract the current page state:
        - URL and title
        - Interactive elements with data-agent-id tags
        - Visible page text (truncated)
        """
        url = self.page.url
        title = self.page.title()

        # Inject data-agent-id into interactive elements and extract them
        js_script = """
        () => {
            let idCounter = 1;
            const elements = document.querySelectorAll(
                'a, button, input, textarea, select, [role="button"], [role="link"], [role="tab"], [role="checkbox"], [role="option"], [role="menuitem"]'
            );
            elements.forEach(el => {
                const style = window.getComputedStyle(el);
                if (style.display === 'none' || style.visibility === 'hidden' || el.offsetWidth === 0) return;
                el.setAttribute('data-agent-id', idCounter);
                idCounter++;
            });

            let interactive = [];
            document.querySelectorAll('[data-agent-id]').forEach(el => {
                const text = (el.innerText || el.value || el.placeholder || el.getAttribute('aria-label') || el.title || '').trim().replace(/\\n/g, ' ').substring(0, 120);
                if (text !== '') {
                    const tag = el.tagName.toLowerCase();
                    const type = el.getAttribute('type') || '';
                    const href = el.getAttribute('href') || '';
                    let desc = `[${el.getAttribute('data-agent-id')}] <${tag}`;
                    if (type) desc += ` type="${type}"`;
                    if (href) desc += ` href="${href.substring(0, 80)}"`;
                    desc += `> ${text}`;
                    interactive.push(desc);
                }
            });

            const bodyText = document.body.innerText || "";
            return { interactive: interactive, text: bodyText };
        }
        """
        try:
            result = self.page.evaluate(js_script)
        except Exception:
            return {"url": url, "title": title, "elements": [], "text": ""}

        elements = result.get("interactive", [])[:ELEMENT_LIMIT]
        text = result.get("text", "")[:PAGE_TEXT_LIMIT]

        return {
            "url": url,
            "title": title,
            "elements": elements,
            "text": text,
        }

    def extract_full_text(self) -> str:
        """Extract full visible text from the page (for data collection steps)."""
        try:
            return self.page.evaluate("document.body.innerText || ''")
        except Exception:
            return ""

    def close(self):
        try:
            self.browser.close()
            self._p.stop()
        except Exception:
            pass


# ── Singleton ──────────────────────────────────────────────────────────────────

_browser_instance = None

def _get_browser() -> BrowserSession:
    global _browser_instance
    if _browser_instance is None:
        _browser_instance = BrowserSession()
    return _browser_instance


# ── Autopilot LLM Loop ────────────────────────────────────────────────────────

def _build_autopilot_prompt(task: str, page_state: dict, collected_data: list, step: int) -> str:
    """Build the prompt for the autopilot LLM at each step."""
    
    # CRITICAL: Sanitize element text to remove HTML angle brackets
    # that confuse the LLM into producing broken JSON
    sanitized_elements = []
    for elem in (page_state["elements"] or []):
        # Replace <tag ...> patterns with [tag ...] to prevent JSON-breaking HTML
        clean = re.sub(r'<(\w+)', r'[\1', elem)
        clean = re.sub(r'>', r']', clean)
        clean = clean.replace('"', "'")  # Replace inner quotes with single quotes
        sanitized_elements.append(clean)
    
    elements_str = "\n".join(sanitized_elements) if sanitized_elements else "(no interactive elements found)"
    
    # Show a summary of what we've collected so far
    collected_summary = ""
    if collected_data:
        collected_summary = f"\n\nDATA COLLECTED SO FAR ({len(collected_data)} items):\n"
        for i, item in enumerate(collected_data[-3:]):  # Show last 3 to save context
            try:
                collected_summary += f"  Item {len(collected_data) - 2 + i}: {json.dumps(item, ensure_ascii=False)[:200]}\n"
            except Exception:
                collected_summary += f"  Item {len(collected_data) - 2 + i}: (data present)\n"

    # Truncate page text and remove any characters that could break JSON
    page_text = page_state['text'][:2000].replace('"', "'").replace('\\', '/')

    return f"""You are a Browser Autopilot. You are on step {step}/{MAX_BROWSER_STEPS}.

YOUR TASK: {task}

CURRENT PAGE:
  URL: {page_state['url']}
  Title: {page_state['title']}

INTERACTIVE ELEMENTS (use the ID number to click/type):
{elements_str}

PAGE TEXT (truncated):
{page_text}
{collected_summary}
AVAILABLE ACTIONS (respond with exactly ONE JSON object):

1. Click an element:
   {{"action": "click", "element_id": 42, "reason": "clicking the India filter"}}

2. Type into an input:
   {{"action": "type", "element_id": 7, "text": "search query", "reason": "typing search term"}}

3. Navigate to a new URL:
   {{"action": "navigate", "url": "https://...", "reason": "going to company detail page"}}

4. Go back to previous page:
   {{"action": "go_back", "reason": "returning to the company list"}}

5. Scroll down to see more content:
   {{"action": "scroll", "reason": "loading more companies"}}

6. Extract/save data from this page (ONLY use plain text values, NO HTML):
   {{"action": "extract", "data": {{"<field1>": "value", "<field2>": "value"}}, "reason": "saving company info"}}

7. Finish — you have completed the task:
   {{"action": "done", "summary": "description of what was accomplished"}}

CRITICAL RULES:
- Respond with ONLY a single valid JSON object. No markdown, no explanation, no HTML.
- All string values in your JSON must be plain text. NEVER include HTML tags like <a>, <div>, etc.
- Use element IDs from the INTERACTIVE ELEMENTS list above. Do NOT guess IDs.
- Extract ONE company at a time. Do NOT put multiple companies in a single extract action.
- Make sure your extracted `data` dictionary keys EXACTLY match the data fields requested in YOUR TASK.
- DO NOT get stuck in a loop. If you clicked an element and the page didn't change, DO NOT click it again.
- After clicking a filter or link, the page will reload. You will see the new state on the next step.
- Use "extract" to save each piece of data you find. All extracted data will be returned at the end.
- Use "go_back" to return to the list page after extracting data from a detail page.
- If you cannot find what you need, use "done" with a summary explaining what happened.
"""


def _run_autopilot(url: str, task: str, model: str = "llama3.1:8b") -> dict:
    """
    The core Browser Autopilot loop.
    Navigates to URL, then iteratively asks the LLM what to do next.
    
    Hardened features:
    - Auto-saves collected data to disk after every extract (crash recovery)
    - Graceful JSON parse error handling (retry, don't crash)
    - Returns partial data even on total failure
    """
    from core.models import get_conversation_session
    from datetime import datetime

    browser = _get_browser()
    collected_data = []
    parse_failures = 0
    max_parse_failures = 5  # Give up after 5 consecutive parse failures

    # Setup auto-save recovery file
    os.makedirs(AUTOSAVE_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    recovery_file = os.path.join(AUTOSAVE_DIR, f"autopilot_{timestamp}.txt")
    
    def _autosave():
        """Save collected data to recovery file."""
        if not collected_data:
            return
        try:
            with open(recovery_file, "w", encoding="utf-8") as f:
                f.write(f"# Autopilot Recovery Data\n")
                f.write(f"# Task: {task[:200]}\n")
                f.write(f"# URL: {url}\n")
                f.write(f"# Saved: {datetime.now().isoformat()}\n")
                f.write(f"# Items: {len(collected_data)}\n\n")
                for i, item in enumerate(collected_data):
                    f.write(f"--- ITEM {i+1} ---\n")
                    f.write(json.dumps(item, indent=2, ensure_ascii=False))
                    f.write("\n\n")
            print(f"    💾 Auto-saved {len(collected_data)} items → {recovery_file}")
        except Exception:
            pass

    # Step 0: Navigate to the starting URL
    print(f"  [Autopilot] 🚀 Starting: {url}")
    nav_result = browser.goto(url)
    print(f"  [Autopilot] {nav_result}")

    # Create a dedicated LLM session for the autopilot
    session = get_conversation_session(
        model=model,
        system_prompt="You are a Browser Autopilot. Respond with ONLY a single JSON action object. No text, no markdown. No HTML in your values."
    )

    for step in range(1, MAX_BROWSER_STEPS + 1):
        try:
            # Read current page state
            page_state = browser.get_page_state()

            # Build prompt and ask LLM
            prompt = _build_autopilot_prompt(task, page_state, collected_data, step)
            raw_response = session.chat(prompt)

            # Parse the LLM's decision
            decision = extract_json(raw_response)
            
            if decision is None:
                parse_failures += 1
                print(f"  [Autopilot] Step {step}: ⚠️ JSON parse failed ({parse_failures}/{max_parse_failures}). Retrying...")
                
                if parse_failures >= max_parse_failures:
                    print(f"  [Autopilot] ❌ Too many parse failures. Stopping with {len(collected_data)} items.")
                    break
                
                # Ask LLM to fix its response
                raw_response = session.chat(
                    "CRITICAL: Your response was NOT valid JSON. You MUST respond with ONLY a JSON object like "
                    '{"action": "click", "element_id": 5, "reason": "..."} — no HTML, no markdown, no extra text.'
                )
                decision = extract_json(raw_response)
                if decision is None:
                    print(f"  [Autopilot] Step {step}: ❌ Still invalid. Skipping step.")
                    continue
            
            # Reset parse failure counter on success
            parse_failures = 0

            action = decision.get("action", "")
            reason = decision.get("reason", "")
            print(f"  [Autopilot] Step {step}: {action} — {reason}")

            # ── Programmatic Anti-Loop Circuit Breaker ─────────────────────
            current_action_signature = f"{action}_{decision.get('element_id', '')}_{decision.get('url', '')}"
            current_page_signature = hash(page_state["text"])
            
            if step > 1:
                # If we are doing the exact same thing on the exact same page, block it.
                if getattr(session, "_last_action_sig", None) == current_action_signature and \
                   getattr(session, "_last_page_sig", None) == current_page_signature:
                    print(f"  [Autopilot] 🛑 Circuit Breaker: Blocked repeating '{action}' on unchanged page. Forcing retry.")
                    raw_response = session.chat(
                        "CRITICAL RULE VIOLATION: You just tried to repeat the exact same action on the exact same page, and it did not change the page state. You are stuck in a loop. DO NOT repeat the last action. Try clicking something else, or use 'go_back', or use 'done'."
                    )
                    # We will continue to the next loop iteration, which will read the page state and ask again
                    # But first, we shouldn't execute the blocked action.
                    continue
            
            session._last_action_sig = current_action_signature
            session._last_page_sig = current_page_signature

            # ── Execute the action ─────────────────────────────────────────
            if action == "click":
                eid = decision.get("element_id")
                if eid is not None:
                    result = browser.click(int(eid))
                    print(f"    → {result}")
                else:
                    print(f"    → Missing element_id")

            elif action == "type":
                eid = decision.get("element_id")
                text = decision.get("text", "")
                if eid is not None and text:
                    result = browser.type_text(int(eid), text)
                    print(f"    → {result}")

            elif action == "navigate":
                new_url = decision.get("url", "")
                if new_url:
                    # Handle relative URLs
                    if new_url.startswith("/"):
                        from urllib.parse import urlparse as _urlparse
                        parsed = _urlparse(url)
                        new_url = f"{parsed.scheme}://{parsed.netloc}{new_url}"
                    result = browser.goto(new_url)
                    print(f"    → {result}")

            elif action == "go_back":
                result = browser.go_back()
                print(f"    → {result}")

            elif action == "scroll":
                result = browser.scroll_down()
                print(f"    → {result}")

            elif action == "extract":
                data = decision.get("data", {})
                if data:
                    collected_data.append(data)
                    print(f"    → Saved data item #{len(collected_data)}: {json.dumps(data, ensure_ascii=False)[:150]}")
                    _autosave()  # Auto-save after every extract

            elif action == "done":
                summary = decision.get("summary", "Task completed.")
                print(f"  [Autopilot] ✅ Done: {summary}")
                
                _autosave()
                clean_json_path = None
                if collected_data:
                    output_dir = os.path.join(os.getcwd(), "archive", "outputs")
                    os.makedirs(output_dir, exist_ok=True)
                    from datetime import datetime
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    clean_json_path = os.path.join(output_dir, f"browser_data_{timestamp}.json")
                    try:
                        with open(clean_json_path, "w", encoding="utf-8") as f:
                            json.dump(collected_data, f, indent=2, ensure_ascii=False)
                    except Exception:
                        pass
                        
                return {
                    "success": True,
                    "summary": summary,
                    "total_items": len(collected_data),
                    "steps_taken": step,
                    "recovery_file": recovery_file if collected_data else None,
                    "_MEMORY_FILE": clean_json_path if clean_json_path else None
                }

            else:
                print(f"  [Autopilot] Step {step}: Unknown action '{action}'. Skipping.")

        except Exception as e:
            print(f"  [Autopilot] Step {step}: 💥 Error: {str(e)[:200]}")
            _autosave()  # Save what we have before potentially crashing
            continue  # Don't crash the loop — keep going

    # If we hit max steps or exited the loop
    _autosave()
    print(f"  [Autopilot] ⚠️ Finished after {MAX_BROWSER_STEPS} steps with {len(collected_data)} items.")
    
    clean_json_path = None
    if collected_data:
        output_dir = os.path.join(os.getcwd(), "archive", "outputs")
        os.makedirs(output_dir, exist_ok=True)
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        clean_json_path = os.path.join(output_dir, f"browser_data_{timestamp}.json")
        try:
            with open(clean_json_path, "w", encoding="utf-8") as f:
                json.dump(collected_data, f, indent=2, ensure_ascii=False)
        except Exception:
            pass
            
    return {
        "success": len(collected_data) > 0,
        "summary": f"Autopilot completed with {len(collected_data)} items collected.",
        "total_items": len(collected_data),
        "steps_taken": MAX_BROWSER_STEPS,
        "recovery_file": recovery_file if collected_data else None,
        "_MEMORY_FILE": clean_json_path if clean_json_path else None
    }



# ── Agent Interface ────────────────────────────────────────────────────────────

DESCRIPTION = (
    "A Browser Autopilot Agent powered by Playwright. Use this for any task requiring "
    "real browser interaction: clicking buttons, filling forms, navigating JavaScript-rendered pages, "
    "applying filters, iterating through lists of items, and extracting structured data from dynamic websites. "
    "Unlike web_scraper (which only does static HTTP), this agent can CLICK, TYPE, SCROLL, and NAVIGATE "
    "through multi-step workflows autonomously. Pass a 'task' describing what you want it to do."
)

PARAMETERS = {
    "url": {
        "type": "string",
        "required": True,
        "description": "The starting URL to navigate to.",
    },
    "task": {
        "type": "string",
        "required": True,
        "description": (
            "A natural-language description of what the browser should do. "
            "Example: 'Click the South Asia filter, then India. For each of the first 10 companies, "
            "click on the company, extract the name, URL, batch, and team size, then go back.'"
        ),
    },
    "model": {
        "type": "string",
        "required": False,
        "description": "The LLM model to use for the autopilot brain. Defaults to llama3.1:8b.",
    },
}

from core.models import DEFAULT_MODEL

def browser_agent(url: str, task: str, model: str = DEFAULT_MODEL) -> dict:
    """
    The Browser Autopilot entry point.
    Called by the Orchestrator like any other agent.
    Internally runs its own ReAct loop against a real Playwright browser.
    """
    if sync_playwright is None:
        return {"error": "Playwright is not installed. Run: pip install playwright && playwright install"}

    try:
        result = _run_autopilot(url=url, task=task, model=model)
        return result
    except Exception as e:
        return {"error": f"Browser Autopilot failed: {str(e)}"}
