# Meta Agent (meta_agent.py)

## Brief Description
Create a new agent tool by saving a complete Python script to the agents/ folder.

## Prerequisites
1. **Dependencies**: Ensure all required Python packages for this agent are installed.

## Step-by-Step Setup Guide
1. Check the `agents/meta_agent.py` file for any hardcoded `os.environ.get()` calls to see what API keys it expects.
2. Export any required API keys to your environment.
3. Make sure you are running the system within the `.venv` virtual environment.

## How to Update
- The code for this agent lives in `agents/meta_agent.py`.
- To modify its behavior or add new parameters, edit the `PARAMETERS` dictionary and the primary function in the Python file.
