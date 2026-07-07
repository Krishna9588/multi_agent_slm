# Auth Agent (auth_agent.py)

## Brief Description
An Interactive Authentication Agent. Use this when the Swarm hits a login wall or 401 error.

## Prerequisites
1. **Auth Provider**: e.g., Firebase, Auth0, or internal secrets.

## Step-by-Step Setup Guide
1. If using Firebase, download your `serviceAccountKey.json` from the Firebase Console.
2. Place it in the root directory and set `export GOOGLE_APPLICATION_CREDENTIALS="serviceAccountKey.json"`.

## How to Update
- The code for this agent lives in `agents/auth_agent.py`.
- To modify its behavior or add new parameters, edit the `PARAMETERS` dictionary and the primary function in the Python file.
