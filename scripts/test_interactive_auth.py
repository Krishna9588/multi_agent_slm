"""
A simple script to test the new Interactive Session Authentication flow.
Run this script to manually log into GitHub, and then verify that the headless browser
successfully re-uses your logged-in session!
"""
import time
from agents.auth_agent import auth_agent
from agents.browser_agent import get_browser

def run_test():
    print("=== Phase 1: Interactive Authentication ===")
    print("We will now pop open a visible browser. Please log into GitHub.")
    
    # This will open a visible window and wait for the user to press Enter in the terminal
    result = auth_agent(platform="github", login_url="https://github.com/login")
    
    if "error" in result:
        print(f"Auth failed: {result['error']}")
        return
        
    print("\nAuth successful! Session saved.")
    print("Waiting 3 seconds before starting the headless test...")
    time.sleep(3)
    
    print("\n=== Phase 2: Headless Session Re-use ===")
    print("Now we will launch a completely new headless browser (invisible) to visit github.com.")
    
    browser = get_browser()
    # The browser_agent will automatically detect `github_session.json` and inject the cookies!
    browser.goto("https://github.com/")
    
    # Let's extract the accessibility tree to see if it sees the logged-in dashboard
    dom = browser.get_dom()
    
    print("\n--- Extracted Headless DOM (First 500 chars) ---")
    print(dom[:500])
    
    if "Sign in" not in dom and "Dashboard" in dom or "Pull requests" in dom:
        print("\n✅ TEST PASSED: The headless browser is successfully logged into GitHub!")
    else:
        print("\n⚠️ Note: Check the DOM output to see if it shows your logged-in dashboard.")
        
    browser.close()

if __name__ == "__main__":
    run_test()
