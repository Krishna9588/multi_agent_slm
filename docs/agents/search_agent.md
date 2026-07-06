# Search Agent (search_agent.py)

## Brief Description
The Search Agent allows the AI Swarm to search the internet for real-time information, news, and links. It is a critical component for fetching up-to-date facts before invoking the web scraper.

## Prerequisites
1. **Python Dependencies**: The system relies on the `ddgs` (DuckDuckGo Search) Python library.

## Step-by-Step Setup Guide
1. **Open your Terminal**: Navigate to your project directory.
2. **Activate Virtual Environment**: If you are using a virtual environment (like `.venv`), activate it by running `source .venv/bin/activate`.
3. **Install the Package**: Run `pip install ddgs`. 
4. *(Note: The older `duckduckgo_search` library is deprecated and will cause the agent to hang. Ensure you install `ddgs` specifically).*

## How to Update
- The code lives in `agents/search_agent.py`.
- If you wish to switch from DuckDuckGo to Google Search or SerpAPI, you can modify the primary `search_agent` function block to use an HTTP request to your preferred Search API instead.
