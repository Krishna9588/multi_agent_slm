import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from agents.setup_guide_agent import setup_guide_agent

def test_setup_guide_agent():
    res = setup_guide_agent("github_agent", "Error: Authentication failed, missing token.")
    assert "github" in str(res).lower() or "token" in str(res).lower()

if __name__ == "__main__":
    res = setup_guide_agent("github_agent", "Error: Authentication failed, missing token.")
    print(res)
