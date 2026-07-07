# Social Media Agent (social_media_agent.py)

## Brief Description
The Social Media Agent acts as a Marketer. It interacts with platforms like Twitter and LinkedIn to read brand mentions, post updates, and analyze the sentiment of trending topics.

## Prerequisites
1. **Developer Accounts**: You need a Twitter Developer Account or LinkedIn Developer Account to get API keys.
2. **Environment Variables**: API keys must be injected into the environment.

## Step-by-Step Setup Guide
1. **Go to Twitter Developer Portal**: Visit [developer.twitter.com](https://developer.twitter.com).
2. **Create an App**: Register a new application to get your API keys.
3. **Generate Tokens**: Generate the Consumer Key, Consumer Secret, Access Token, and Access Token Secret.
4. **Set Environment Variables**: In your terminal, run the following (replace with your actual keys):
   - `export TWITTER_API_KEY="your_key"`
   - `export TWITTER_API_SECRET="your_secret"`
   - `export TWITTER_ACCESS_TOKEN="your_token"`
   - `export TWITTER_ACCESS_SECRET="your_access_secret"`

## How to Update
- The code lives in `agents/social_media_agent.py`.
- Currently, it relies on mock APIs to simulate posting. To enable real posting, install `tweepy` (`pip install tweepy`) and replace the `mock_mentions` blocks with real authenticated API calls using your environment variables.
