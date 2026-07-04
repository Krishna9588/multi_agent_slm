"""
Agent: api_discovery_agent
--------------------------
Dynamically figures out how to talk to undocumented or 3rd-party REST/GraphQL APIs.
Can fetch and parse OpenAPI specs, construct payloads, and execute HTTP requests.
"""

import requests
import json
import time

DESCRIPTION = (
    "An API Integrator Agent. Use this to interact with external REST APIs dynamically. "
    "You can use it to fetch an OpenAPI/Swagger JSON to understand the endpoints, "
    "or you can use it to directly send GET/POST requests with custom headers and payloads."
)

PARAMETERS = {
    "action": {
        "type": "string",
        "required": True,
        "description": "Must be one of: 'analyze_openapi', 'send_request'.",
    },
    "url": {
        "type": "string",
        "required": True,
        "description": "The URL of the API endpoint or the OpenAPI JSON spec.",
    },
    "method": {
        "type": "string",
        "required": False,
        "description": "HTTP method ('GET', 'POST', 'PUT', 'DELETE'). Defaults to 'GET'. Required for 'send_request'.",
    },
    "headers": {
        "type": "string",
        "required": False,
        "description": "A JSON string of HTTP headers (e.g., '{\"Authorization\": \"Bearer token\"}').",
    },
    "payload": {
        "type": "string",
        "required": False,
        "description": "A JSON string representing the request body (for POST/PUT).",
    }
}

def api_discovery_agent(
    action: str, 
    url: str, 
    method: str = "GET", 
    headers: str = "{}", 
    payload: str = "{}"
) -> dict:
    """Interacts with external APIs."""
    action = action.lower().strip()
    
    try:
        req_headers = json.loads(headers) if headers else {}
    except json.JSONDecodeError:
        return {"error": "Invalid JSON format in 'headers' parameter."}
        
    try:
        req_payload = json.loads(payload) if payload else {}
    except json.JSONDecodeError:
        return {"error": "Invalid JSON format in 'payload' parameter."}

    if action == "analyze_openapi":
        try:
            response = requests.get(url, headers=req_headers, timeout=10)
            response.raise_for_status()
            spec = response.json()
            
            # Extract just the paths and methods to prevent context blowout
            endpoints = []
            paths = spec.get("paths", {})
            for path, methods in paths.items():
                for m_name, m_details in methods.items():
                    summary = m_details.get("summary", "No summary")
                    endpoints.append(f"{m_name.upper()} {path} - {summary}")
                    
            if not endpoints:
                return {"success": True, "endpoints": "No endpoints found in the spec."}
                
            return {
                "success": True, 
                "message": f"Successfully parsed OpenAPI spec. Found {len(endpoints)} endpoints.",
                "endpoints": endpoints[:50] # Limit to 50 to save context window
            }
            
        except Exception as e:
            return {"error": f"Failed to analyze OpenAPI spec: {str(e)}"}
            
    elif action == "send_request":
        method = method.upper().strip()
        if method not in ["GET", "POST", "PUT", "DELETE", "PATCH"]:
            return {"error": f"Unsupported HTTP method: {method}"}
            
        try:
            # Execute request
            response = requests.request(
                method=method,
                url=url,
                headers=req_headers,
                json=req_payload if method in ["POST", "PUT", "PATCH"] else None,
                params=req_payload if method == "GET" else None,
                timeout=15
            )
            
            # Detect Rate Limiting
            if response.status_code == 429:
                retry_after = response.headers.get("Retry-After", 5)
                return {
                    "error": f"Rate limited (429). You must wait {retry_after} seconds before trying again.",
                    "status_code": 429,
                    "retry_after": retry_after
                }
                
            # Attempt to parse response as JSON, fallback to text
            try:
                data = response.json()
            except ValueError:
                data = response.text[:2000] # Truncate massive HTML/Text responses
                
            return {
                "success": response.ok,
                "status_code": response.status_code,
                "response": data
            }
            
        except requests.exceptions.Timeout:
            return {"error": "Request timed out after 15 seconds."}
        except Exception as e:
            return {"error": f"API request failed: {str(e)}"}
            
    else:
        return {"error": "Invalid action. Use 'analyze_openapi' or 'send_request'."}
