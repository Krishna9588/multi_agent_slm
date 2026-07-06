# Email Agent (email_agent.py)

## Brief Description
The Communicator Agent (Email). Use this to read the user

## Prerequisites
1. **Google Cloud Account**: You must have a Google Cloud Platform account.
2. **OAuth Credentials**: A `credentials.json` file for Google Workspace APIs.

## Step-by-Step Setup Guide
1. Go to the [Google Cloud Console](https://console.cloud.google.com/).
2. Create a new project and enable the respective API (Gmail API or Google Calendar API).
3. Navigate to **APIs & Services > Credentials**.
4. Create **OAuth 2.0 Client IDs** (Desktop App type).
5. Download the JSON file and rename it to `credentials.json`.
6. Place `credentials.json` in the root of this project. On first run, it will open a browser to authenticate and create `token.pickle`.

## How to Update
- The code for this agent lives in `agents/email_agent.py`.
- To modify its behavior or add new parameters, edit the `PARAMETERS` dictionary and the primary function in the Python file.
