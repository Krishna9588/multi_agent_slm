# Autonomous Swarm: Capability & Prompt Guide

This document outlines the capabilities of the Swarm based on the number of agents required to fulfill a request. It serves as a guide for what the orchestrator can natively handle versus what requires complex multi-agent routing.

---

## Level 0: Pure LLM (0 Agents Required)
These requests do not trigger any tools. They rely purely on the Orchestrator's internal weights and training data.

**Example Prompts:**
- *"Explain the difference between a TCP and UDP connection."*
- *"Write a Python script to reverse a linked list."*
- *"Summarize the core themes of George Orwell's 1984."*
- *"Translate 'Hello, how are you' into Japanese."*

---

## Level 1: Single-Agent Execution (1 Agent Required)
These requests require the Orchestrator to reach out to the real world using exactly one specialized tool.

**Example Prompts:**
- *"Scrape the headline text from https://news.ycombinator.com."* 
  *(Requires: `web_scraper`)*
- *"Read my unread emails."* 
  *(Requires: `email_agent`)*
- *"What are the table names in our local database.db?"* 
  *(Requires: `sql_db_agent`)*
- *"Check my calendar to see if I have any meetings tomorrow."* 
  *(Requires: `calendar_agent`)*
- *"Clone the react repository from github into my workspace."* 
  *(Requires: `github_agent`)*

---

## Level 2: Dual-Agent Synergy (2 Agents Required)
These requests require the Orchestrator to fetch data using one agent, hold it in context, and process or execute it using a second agent.

**Example Prompts:**
- *"Scrape the latest blog post from OpenAI, and save the text to a local markdown file."*
  *(Requires: `web_scraper` -> `file_system_agent`)*
- *"Read my latest unread email, and reply to the sender saying I will look into it."*
  *(Requires: `email_agent(read)` -> `email_agent(send)`)*
- *"Analyze the schema of my database, and then run a query to count how many users are active."*
  *(Requires: `sql_db_agent(get_schema)` -> `sql_db_agent(execute_query)`)*
- *"Take a screenshot of https://apple.com and describe what the main hero image looks like."*
  *(Requires: `browser_agent` -> `vision_agent`)*
- *"Check what people are saying about our brand on Twitter, and save those mentions to our long-term memory DB."*
  *(Requires: `social_media_agent` -> `memory_agent`)*

---

## Level 3: The Complex Swarm (5+ Agents Required)
These are highly autonomous, multi-step goals. The Orchestrator must dynamically plan, recover from errors, and route data across a massive web of tools to achieve the objective.

**Example Prompts:**
- **The Competitor Analysis:** *"Find out what our competitor's pricing is on their website. If you get blocked by Cloudflare, use a real browser to bypass it. Once you find the prices, export them to a CSV, email that CSV to my boss, and create a calendar event for us to discuss it tomorrow."*
  *(Requires: `web_scraper` -> `browser_agent` -> `data_exporter_agent` -> `email_agent` -> `calendar_agent`)*

- **The Automated Developer:** *"Clone this repository from GitHub. Find the API documentation PDF inside it, read it to figure out how their endpoints work. Write a python script using that API, test the script locally in the sandbox, and if it passes, commit and push the changes back to a new branch."*
  *(Requires: `github_agent` -> `file_system_agent` -> `pdf_ocr_agent` -> `code_executor_agent` -> `github_agent`)*

- **The Meeting Archivist:** *"Take the 2-hour audio recording of yesterday's meeting. Transcribe the whole thing. Find any mentions of 'deadlines', query our SQL database to see if those project deadlines exist, update the database if they don't, and post a summary of the new deadlines to our team's Slack API."*
  *(Requires: `audio_transcription_agent` -> `sql_db_agent` -> `api_discovery_agent` -> `memory_agent`)*

- **The Self-Healing Researcher:** *"Deep research the latest advancements in quantum computing. If you fail to find good data or get stuck in a loop, analyze your own failure logs, patch your own system prompt to be a better researcher, and try again until you succeed."*
  *(Requires: `search_agent` -> `deep_research_agent` -> `page_classifier` -> `self_reflection_agent` -> `memory_agent`)*
