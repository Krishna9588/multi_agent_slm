import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from core.swarm import run_swarm, Agent, TransferToAgent
from core.models import DEFAULT_MODEL, SECONDARY_MODEL
from agents.browser_agent import browser_goto, browser_click, browser_type, browser_read, done_browsing

def transfer_to_browser(**kwargs) -> TransferToAgent:
    """Delegates the task to the Browser Agent."""
    return TransferToAgent(browser_agent)

# Define the Browser Agent
browser_agent = Agent(
    name="BrowserAgent",
    model=SECONDARY_MODEL,
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

# Define the Meta Orchestrator
meta_agent = Agent(
    name="MetaOrchestrator",
    model=DEFAULT_MODEL,
    instructions="""You are the Meta-Orchestrator.
Your job is to route tasks. If a user asks to interact with a website or scrape a page dynamically, you MUST call transfer_to_browser.
Do not attempt to answer it yourself.""",
    functions=[transfer_to_browser]
)

def test_swarm_agent_initialization():
    """Verify Swarm agents initialize with correct models and tools."""
    assert browser_agent.name == "BrowserAgent"
    assert len(browser_agent.functions) == 5
    assert meta_agent.name == "MetaOrchestrator"
    assert len(meta_agent.functions) == 1

if __name__ == "__main__":
    print("Starting Multi-Agent Swarm Test...")
    difficult_query = "Go to https://news.ycombinator.com (Hacker News), read the titles of the top 3 articles, and then click on the first article's comments link to read what people are saying."
    result = run_swarm(starting_agent=meta_agent, user_query=difficult_query)
    print("\nFinal Result:")
    print(result)

