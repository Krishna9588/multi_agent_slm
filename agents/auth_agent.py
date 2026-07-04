"""
Agent: auth_agent
-----------------
Specialized agent for handling authentication flows (logins).
Uses Playwright to securely log in to platforms using credentials from .env,
and saves the browser context (cookies/session) so other agents can use it later.
"""

import os
try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright = None
import time

DESCRIPTION = (
    "An Interactive Authentication Agent. Use this when the Swarm hits a login wall or 401 error. "
    "Supported platforms: 'linkedin', 'github', 'generic'. "
    "It opens a visible browser window, pauses the Swarm so the user can log in manually (handling 2FA/OAuth themselves), "
    "and then securely saves the session cookies to disk so the Swarm can continue autonomously."
)

PARAMETERS = {
    "platform": {
        "type": "string",
        "required": True,
        "description": "The platform to log into (e.g., 'linkedin', 'github').",
    },
    "login_url": {
        "type": "string",
        "required": True,
        "description": "The exact URL of the login page.",
    }
}

def auth_agent(platform: str, login_url: str) -> dict:
    """Opens a visible browser for the user to log in, then saves the authentication state."""
    platform = platform.lower().strip()
    
    # Ensure the sessions directory exists
    sessions_dir = os.path.join(os.getcwd(), "archive", "sessions")
    os.makedirs(sessions_dir, exist_ok=True)
    state_file = os.path.join(sessions_dir, f"{platform}_session.json")
    
    try:
        with sync_playwright() as p:
            # Launch in non-headless mode so the user can actually see it and type
            browser = p.chromium.launch(headless=False)
            context = browser.new_context()
            page = context.new_page()
            
            print(f"\n  [AuthAgent] 🛑 PAUSED FOR INTERACTIVE LOGIN")
            print(f"  [AuthAgent] Opening {login_url} in a visible browser window.")
            print(f"  [AuthAgent] Please log in manually (complete 2FA, OAuth, etc.).")
            
            page.goto(login_url, wait_until="domcontentloaded")
            
            # Wait for user to finish in the terminal
            try:
                input(f"  [AuthAgent] Press ENTER here in the terminal once you have successfully logged in... ")
            except (EOFError, KeyboardInterrupt):
                browser.close()
                return {"error": "Authentication cancelled by user."}
                
            print(f"  [AuthAgent] Saving session state to {state_file}...")
            
            # Save the state (cookies, local storage)
            context.storage_state(path=state_file)
            browser.close()
            
        return {
            "success": True,
            "message": f"Successfully authenticated and saved session for {platform}.",
            "auth_state_file": state_file,
            "instruction": f"The browser session is saved to {state_file}. Update browser_agent to load this context."
        }
        
    except Exception as e:
        return {"error": f"Interactive authentication failed: {str(e)}"}
