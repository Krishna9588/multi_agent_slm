"""
Agent: vision_agent
-------------------
Powered by multimodal models to interpret images, screenshots, and visual layouts.
Use this agent to solve visual CAPTCHAs, describe UI elements, or extract text from images.
"""

import os
import base64
from core.models import get_conversation_session, VISION_MODEL, GEMINI_MODELS

DESCRIPTION = (
    "A Multimodal Vision Agent. Pass it an absolute file path to an image (like a screenshot), "
    "and it will use a vision model to analyze and answer questions about it. "
    "Use this for solving CAPTCHAs or understanding visual layouts that text extraction misses."
)

PARAMETERS = {
    "image_path": {
        "type": "string",
        "required": True,
        "description": "Absolute path to the image file (e.g. .png, .jpg) to analyze.",
    },
    "prompt": {
        "type": "string",
        "required": True,
        "description": "The question or instruction about the image (e.g. 'What does this CAPTCHA say?').",
    }
}

def vision_agent(image_path: str, prompt: str) -> dict:
    """Uses a vision model to analyze an image."""
    if not os.path.exists(image_path):
        return {"error": f"Image file not found at {image_path}"}
        
    try:
        with open(image_path, "rb") as image_file:
            raw_bytes = image_file.read()
            encoded_string = base64.b64encode(raw_bytes).decode('utf-8')
            
        # Try local vision model first
        try:
            session = get_conversation_session(model=VISION_MODEL)
            result = session.chat(prompt, images=[encoded_string])
            return {
                "success": True,
                "model_used": VISION_MODEL,
                "vision_analysis": result.strip()
            }
        except Exception as local_e:
            # Fallback to cloud vision model if Gemini API key exists
            if os.getenv("GEMINI_API_KEY") and os.getenv("GEMINI_API_KEY") != "your_gemini_api_key_here":
                cloud_model = "gemini-2.5-flash"
                from google import genai
                from google.genai import types
                client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
                response = client.models.generate_content(
                    model=cloud_model,
                    contents=[
                        types.Part.from_bytes(data=raw_bytes, mime_type="image/png"),
                        prompt
                    ]
                )
                return {
                    "success": True,
                    "model_used": cloud_model,
                    "vision_analysis": response.text.strip()
                }
            raise local_e
        
    except Exception as e:
        return {"error": f"Failed to analyze image: {str(e)}"}
