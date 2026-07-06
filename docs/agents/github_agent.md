# GitHub Agent (github_agent.py)

## Brief Description
The GitHub Agent is a Software Engineer assistant that interacts with Git and GitHub via the CLI. It allows the AI swarm to autonomously clone repositories, create branches, and commit changes to local sandboxes.

## Prerequisites
1. **Git CLI**: Git must be installed on your system.
2. **GitHub Account**: You must have a valid GitHub account.
3. **Authentication**: You must be authenticated via SSH or have a GitHub Personal Access Token (PAT) configured.

## Step-by-Step Setup Guide
1. **Install Git**: If you are on Mac, run `brew install git`. On Linux, run `sudo apt-get install git`.
2. **Generate a Token**: Go to [GitHub Developer Settings](https://github.com/settings/tokens).
3. **Create Token**: Click "Generate new token (classic)" and give it `repo` permissions.
4. **Export Token**: Open your terminal and run `export GITHUB_TOKEN="your_token_here"`.
5. **Set Git Config**: Make sure your git config is set: 
   - `git config --global user.name "Your Name"`
   - `git config --global user.email "your.email@example.com"`

## How to Update
- The code for this agent lives in `agents/github_agent.py`.
- It currently operates exclusively in the `archive/github_repos/` sandbox. To change this sandbox, modify the `SANDBOX_DIR` variable on line 45.
