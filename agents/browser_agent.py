from playwright.sync_api import sync_playwright
import time
import json
from bs4 import BeautifulSoup

import os
from urllib.parse import urlparse

class BrowserSession:
    """A persistent browser session for the swarm."""
    def __init__(self):
        self._p = sync_playwright().start()
        self.browser = self._p.chromium.launch(headless=True)
        self.context = self.browser.new_context()
        self.page = self.context.new_page()
        self.current_session_file = None
        
    def goto(self, url: str):
        print(f"  [Browser] Navigating to {url}")
        
        # Check if we have a saved interactive session for this domain
        domain = urlparse(url).netloc.replace("www.", "").split('.')[0]
        session_file = os.path.join(os.getcwd(), "archive", "sessions", f"{domain}_session.json")
        
        if os.path.exists(session_file) and self.current_session_file != session_file:
            print(f"  [Browser] 🟢 Found saved session for '{domain}'. Injecting cookies...")
            self.page.close()
            self.context.close()
            self.context = self.browser.new_context(storage_state=session_file)
            self.page = self.context.new_page()
            self.current_session_file = session_file
            
        self.page.goto(url, wait_until="networkidle")
        return f"Successfully navigated to {url}"
        
    def click(self, element_id: int):
        print(f"  [Browser] Clicking ID {element_id}")
        selector = f"[data-agent-id='{element_id}']"
        try:
            self.page.click(selector, timeout=5000)
            time.sleep(1) # simple wait for reaction
            return f"Clicked element {element_id}"
        except Exception as e:
            return f"Error clicking element {element_id}: {str(e)}"
        
    def type_text(self, element_id: int, text: str):
        print(f"  [Browser] Typing into ID {element_id}")
        selector = f"[data-agent-id='{element_id}']"
        try:
            self.page.fill(selector, text, timeout=5000)
            return f"Typed text into {element_id}"
        except Exception as e:
            return f"Error typing into {element_id}: {str(e)}"
        
    def get_dom(self) -> str:
        """Injects data-agent-id into interactive elements and returns a simplified accessibility tree."""
        print("  [Browser] Extracting accessibility tree")
        
        js_script = """
        () => {
            let idCounter = 1;
            const elements = document.querySelectorAll('a, button, input, textarea, select, [role="button"], [role="link"]');
            elements.forEach(el => {
                const style = window.getComputedStyle(el);
                if (style.display === 'none' || style.visibility === 'hidden' || el.offsetWidth === 0) return;
                el.setAttribute('data-agent-id', idCounter);
                idCounter++;
            });
            
            let interactive = [];
            document.querySelectorAll('[data-agent-id]').forEach(el => {
                const text = el.innerText || el.value || el.placeholder || el.getAttribute('aria-label') || el.title;
                if (text && text.trim() !== '') {
                    interactive.push(`[ID: ${el.getAttribute('data-agent-id')}] ${el.tagName.toLowerCase()} - ${text.trim().replace(/\\n/g, ' ').substring(0, 100)}`);
                }
            });
            
            // Extract main text
            const bodyText = document.body.innerText || "";
            return `--- INTERACTIVE ELEMENTS ---\\n` + interactive.join('\\n') + `\\n\\n--- PAGE TEXT ---\\n` + bodyText.substring(0, 3000);
        }
        """
        result = self.page.evaluate(js_script)
        return result
        
    def close(self):
        self.browser.close()
        self._p.stop()

# Global browser instance (lazily initialized)
_browser_instance = None

def get_browser() -> BrowserSession:
    global _browser_instance
    if _browser_instance is None:
        _browser_instance = BrowserSession()
    return _browser_instance

# ── Agent Functions ──

def browser_goto(url: str) -> str:
    """Navigates the browser to a specific URL."""
    return get_browser().goto(url)

def browser_click(element_id: int) -> str:
    """Clicks an element on the page using its integer element_id (found via browser_read)."""
    return get_browser().click(element_id)

def browser_type(element_id: int, text: str) -> str:
    """Types text into an input field using its integer element_id (found via browser_read)."""
    return get_browser().type_text(element_id, text)

def browser_read() -> str:
    """Reads the current visible text content of the page."""
    return get_browser().get_dom()

def done_browsing(extracted_data: str) -> str:
    """Call this when you have successfully found and extracted the information the user wanted."""
    return f"FINAL_DATA: {extracted_data}"

DESCRIPTION = (
    "A Playwright-powered Browser Automation Agent that can render JavaScript, bypass basic bot protection, "
    "and interact with the DOM dynamically. Use this when `web_scraper` fails due to React/JS or Cloudflare."
)

PARAMETERS = {
    "url": {
        "type": "string",
        "required": True,
        "description": "The URL to navigate to and begin interacting with.",
    }
}

def browser_agent(url: str) -> dict:
    """
    Since this is a stateful agent, the actual Swarm handoff is handled by the orchestrator.
    This function simply acts as an entry point for the orchestrator to trigger the browser loop.
    We return a TransferToAgent signal to the Orchestrator.
    """
    from core.swarm import TransferToAgent, Agent
    
    # We define the Browser Agent's configuration for the Swarm Router
    browser_agent_config = Agent(
        name="BrowserAgent",
        model="llama3.2:3b",
        instructions="""You are a Browser Automation Agent.
You can navigate the web, click elements, and read the page.
CRITICAL INSTRUCTION: You CANNOT use CSS selectors to click or type. You MUST use the integer `element_id`.
Workflow:
1. Call `browser_goto` to load the page.
2. Call `browser_read` to extract the Accessibility Tree. The tree will show elements like `[ID: 15] button: Submit`.
3. Call `browser_click` or `browser_type` using the EXACT integer ID (e.g. `element_id: 15`) from the tree. DO NOT guess IDs.
4. If you have extracted the final information, call `done_browsing`.
Always call tools to interact with the web. Do not guess.""",
        functions=[browser_goto, browser_click, browser_type, browser_read, done_browsing]
    )
    
    # We return the special Transfer command to the main Orchestrator
    # Note: We also pass the starting URL so the orchestrator knows what to tell the browser
    return {"transfer_to": browser_agent_config, "initial_instruction": f"Go to {url} and read the page."}
