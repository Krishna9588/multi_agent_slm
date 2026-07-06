import sys
sys.path.insert(0, '.')

from core.swarm import run_swarm, Agent, TransferToAgent
from agents.browser_agent import browser_goto, browser_click, browser_type, browser_read, done_browsing

def transfer_to_browser(**kwargs) -> TransferToAgent:
    """Delegates the task to the Browser Agent."""
    return TransferToAgent(browser_agent)

# Define the Browser Agent
# Using phi4-mini:3.8b for the browser agent because it's great at tool calling
browser_agent = Agent(
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

# Define the Meta Orchestrator
# Using qwen3:4b (since that's what's in OLLAMA_MODELS in models.py) for the orchestrator
meta_agent = Agent(
    name="MetaOrchestrator",
    model="gemma4:e2b-mlx",
    instructions="""You are the Meta-Orchestrator.
Your job is to route tasks. If a user asks to interact with a website or scrape a page dynamically, you MUST call transfer_to_browser.
Do not attempt to answer it yourself.""",
    functions=[transfer_to_browser]
)

print("Starting Multi-Agent Swarm Test...")
difficult_query = "Go to https://news.ycombinator.com (Hacker News), read the titles of the top 3 articles, and then click on the first article's comments link to read what people are saying."
result = run_swarm(starting_agent=meta_agent, user_query=difficult_query)
print("\nFinal Result:")
print(result)

