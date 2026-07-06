import os
import re

AGENT_DOCS_DIR = "docs/agents"
os.makedirs(AGENT_DOCS_DIR, exist_ok=True)

# Helper to generate doc content
def generate_doc(agent_file):
    agent_name = agent_file.replace(".py", "")
    if agent_name.startswith("_") or agent_name in ["schemas", "setup_guide_agent", "test_tool"]:
        return

    # Extract description
    path = os.path.join("agents", agent_file)
    with open(path, "r") as f:
        content = f.read()
    
    desc_match = re.search(r'DESCRIPTION\s*=\s*(?:\(\s*)?["\'](.*?)["\']', content, re.DOTALL)
    desc = desc_match.group(1).replace('\n', ' ').strip() if desc_match else f"The {agent_name} tool."

    # Determine specific setup instructions based on agent name
    prereqs = ""
    steps = ""
    
    if "email" in agent_name or "calendar" in agent_name or "google" in agent_name:
        prereqs = "1. **Google Cloud Account**: You must have a Google Cloud Platform account.\n2. **OAuth Credentials**: A `credentials.json` file for Google Workspace APIs."
        steps = "1. Go to the [Google Cloud Console](https://console.cloud.google.com/).\n2. Create a new project and enable the respective API (Gmail API or Google Calendar API).\n3. Navigate to **APIs & Services > Credentials**.\n4. Create **OAuth 2.0 Client IDs** (Desktop App type).\n5. Download the JSON file and rename it to `credentials.json`.\n6. Place `credentials.json` in the root of this project. On first run, it will open a browser to authenticate and create `token.pickle`."
    elif "sql" in agent_name or "db" in agent_name:
        prereqs = "1. **Database Engine**: PostgreSQL, MySQL, or SQLite.\n2. **Connection String**: The Database URI."
        steps = "1. Ensure your database is running and accessible.\n2. Export the connection string in your environment:\n   `export DATABASE_URL=\"postgresql://user:password@localhost:5432/dbname\"`"
    elif "browser" in agent_name or "scraper" in agent_name:
        prereqs = "1. **Playwright/Selenium**: Browser automation drivers.\n2. **Dependencies**: Required pip packages."
        steps = "1. Install dependencies: `pip install playwright markdownify`.\n2. Install browser binaries: `playwright install`.\n3. (Optional) Set up proxies if scraping heavily restricted sites."
    elif "vision" in agent_name or "ocr" in agent_name or "audio" in agent_name:
        prereqs = "1. **External API Keys**: Keys for specialized vision or audio models (e.g. OpenAI, Anthropic).\n2. **Local Packages**: Tesseract or ffmpeg."
        steps = "1. Install system dependencies if using local processing: `brew install tesseract ffmpeg`.\n2. If using cloud APIs, export your keys: `export OPENAI_API_KEY=\"sk-...\"`."
    elif "auth" in agent_name:
        prereqs = "1. **Auth Provider**: e.g., Firebase, Auth0, or internal secrets."
        steps = "1. If using Firebase, download your `serviceAccountKey.json` from the Firebase Console.\n2. Place it in the root directory and set `export GOOGLE_APPLICATION_CREDENTIALS=\"serviceAccountKey.json\"`."
    elif "external" in agent_name or "api" in agent_name:
        prereqs = "1. **API Keys**: Keys for whatever external service you are attempting to contact."
        steps = "1. Identify the third-party service the agent needs to hit.\n2. Export the appropriate token to your terminal environment before running the swarm."
    else:
        prereqs = "1. **Dependencies**: Ensure all required Python packages for this agent are installed."
        steps = f"1. Check the `{path}` file for any hardcoded `os.environ.get()` calls to see what API keys it expects.\n2. Export any required API keys to your environment.\n3. Make sure you are running the system within the `.venv` virtual environment."

    md_content = f"""# {agent_name.replace('_', ' ').title()} ({agent_file})

## Brief Description
{desc}

## Prerequisites
{prereqs}

## Step-by-Step Setup Guide
{steps}

## How to Update
- The code for this agent lives in `agents/{agent_file}`.
- To modify its behavior or add new parameters, edit the `PARAMETERS` dictionary and the primary function in the Python file.
"""
    
    doc_path = os.path.join(AGENT_DOCS_DIR, f"{agent_name}.md")
    # Don't overwrite the 3 we already perfectly tailored manually
    if agent_name not in ["github_agent", "search_agent", "social_media_agent", "data_structuring_agent"]:
        with open(doc_path, "w") as f:
            f.write(md_content)

for file in os.listdir("agents"):
    if file.endswith(".py"):
        generate_doc(file)

print("Generated MD docs for all agents!")
