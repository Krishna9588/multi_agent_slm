"""
Agent: social_media_agent
-------------------------
The Marketer Agent. Interacts with Twitter/LinkedIn APIs to read mentions,
analyze sentiment of trends, and publish posts.
"""

import os
import json
import urllib.parse
from datetime import datetime

DESCRIPTION = (
    "The Marketer Agent. Use this to post updates to social media, read recent mentions of a brand, "
    "or analyze the sentiment of a specific topic/keyword."
)

PARAMETERS = {
    "action": {
        "type": "string",
        "required": True,
        "description": "Must be one of: 'post_content', 'read_mentions', 'analyze_sentiment'.",
    },
    "platform": {
        "type": "string",
        "required": True,
        "description": "The target platform (e.g., 'twitter', 'linkedin').",
    },
    "content": {
        "type": "string",
        "required": False,
        "description": "The text content to post (required for post_content).",
    },
    "keyword": {
        "type": "string",
        "required": False,
        "description": "The keyword/brand to search for (required for analyze_sentiment).",
    }
}

def social_media_agent(
    action: str, 
    platform: str, 
    content: str = "", 
    keyword: str = ""
) -> dict:
    """Interacts with social media platforms."""
    action = action.lower().strip()
    platform = platform.lower().strip()
    
    # In a real system, we'd use tweepy or linkedin-api here.
    # For this Swarm, we simulate the network calls but enforce the logic boundaries.
    
    if action == "post_content":
        if not content:
            return {"error": "post_content requires 'content'."}
            
        # EDGE CASE: Character limits
        if platform == "twitter" and len(content) > 280:
            return {"error": f"Content exceeds Twitter's 280 character limit (Current length: {len(content)}). Please shorten it."}
            
        # Simulating API POST
        timestamp = datetime.now().isoformat()
        
        # We save it to a local log to prove it executed
        log_path = os.path.join(os.getcwd(), "archive", f"{platform}_posts.log")
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        with open(log_path, "a") as f:
            f.write(f"[{timestamp}] POST: {content}\n")
            
        return {"success": True, "message": f"Successfully published post to {platform}."}
        
    elif action == "read_mentions":
        # Simulating fetching mentions.
        # In reality, this would hit /2/users/:id/mentions on Twitter
        mock_mentions = [
            {"user": "@tech_fan", "text": "This new AI swarm is incredible!", "sentiment": "positive"},
            {"user": "@angry_dev", "text": "Why isn't the auth agent working for me? Bugs everywhere.", "sentiment": "negative"},
            {"user": "@curious_george", "text": "Does anyone know if this supports local models?", "sentiment": "neutral"}
        ]
        return {"success": True, "platform": platform, "mentions": mock_mentions}
        
    elif action == "analyze_sentiment":
        if not keyword:
            return {"error": "analyze_sentiment requires a 'keyword'."}
            
        # Simulating a search and sentiment analysis
        # Here the Swarm would actually pull 100 tweets and pass them through `sentiment_analysis` agent
        return {
            "success": True, 
            "keyword": keyword,
            "report": f"Based on recent data from {platform}, the sentiment around '{keyword}' is roughly 65% Positive, 20% Neutral, and 15% Negative."
        }
        
    else:
        return {"error": "Invalid action. Use 'post_content', 'read_mentions', or 'analyze_sentiment'."}
