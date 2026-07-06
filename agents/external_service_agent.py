"""
Agent: external_service_agent
------------------------------
Dynamic bridge between the orchestrator and external scraping platforms
(Apify, Bright Data, and extensible to ScraperAPI, etc.).

Handles:
  - Human-in-the-loop API token management (checks .env, prompts if missing,
    saves in real-time for future sessions)
  - LLM-driven actor/service selection from a curated catalog
  - REST API execution against external platforms (no extra pip deps)
  - Isolated data persistence in external_data/ directory

Primary function: external_service_agent(query, url, platform, max_items)
"""

import json
import os
import re
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from core.models import get_conversation_session, DEFAULT_MODEL

# ── Agent metadata (shown to the LLM orchestrator) ────────────────────────────

DESCRIPTION = (
    "Calls external cloud scraping platforms (Apify, Bright Data) to extract data from "
    "websites that block normal scraping — like LinkedIn, Instagram, Twitter/X, "
    "Amazon, or any JS-heavy/auth-gated site. "
    "Use this when web_scraper fails or returns a login page, or when the user "
    "explicitly asks to scrape LinkedIn, Instagram, Twitter, Amazon, Google Maps, etc. "
    "Handles API tokens automatically (asks user if missing). "
    "Saves all fetched data to external_data/ for later reuse. "
    "Supports two platforms: 'apify' (default) and 'brightdata' (5K free credits/month)."
)

PARAMETERS = {
    "query": {
        "type":        "string",
        "required":    True,
        "description": (
            "A natural-language description of what to scrape. "
            "E.g. 'Scrape LinkedIn job postings for Python Engineer' or "
            "'Get Google Maps businesses for coffee shops in NYC'."
        ),
    },
    "url": {
        "type":        "string",
        "required":    False,
        "description": (
            "Optional specific URL to scrape. If provided, this URL is passed "
            "directly to the selected actor/service."
        ),
    },
    "platform": {
        "type":        "string",
        "required":    False,
        "description": (
            "Which external platform to use. Default is 'auto' (agent decides). "
            "Currently supported: apify, brightdata. Future: scraperapi."
        ),
    },
    "max_items": {
        "type":        "integer",
        "required":    False,
        "description": "Maximum number of items to fetch. Default is 10.",
    },
}

# ── Paths ──────────────────────────────────────────────────────────────────────

# Project root (two levels up from agents/)
_PROJECT_ROOT  = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_ENV_FILE      = os.path.join(_PROJECT_ROOT, ".env")
_DATA_ROOT     = os.path.join(_PROJECT_ROOT, "external_data")
_LOG_FILE      = os.path.join(_DATA_ROOT, "logs", "request_log.jsonl")

# Catalog file per platform
_CATALOG_FILES = {
    "apify":      os.path.join(_DATA_ROOT, "apify_actors.json"),
    "brightdata": os.path.join(_DATA_ROOT, "brightdata_actors.json"),
}

# ── Token-to-env-var mapping per platform ──────────────────────────────────────

_TOKEN_ENV_MAP = {
    "apify":      "APIFY_TOKEN",
    "brightdata": "BRIGHTDATA_TOKEN",
    "scraperapi": "SCRAPERAPI_KEY",
}

# API base URLs per platform
_APIFY_API_BASE      = "https://api.apify.com/v2"
_BRIGHTDATA_API_BASE = "https://api.brightdata.com/datasets/v3"

# Sync run timeout (seconds)
_SYNC_TIMEOUT = 300  # 5 minutes


# ── Token Management (Human-in-the-Loop) ──────────────────────────────────────

def _resolve_tokens(platform: str = "apify") -> list[str]:
    """
    Resolve API tokens for the given platform. Supports multiple keys.

    Resolution order:
      1. Check os.environ for {ENV_VAR} and {ENV_VAR}_1, {ENV_VAR}_2, etc.
      2. If none, HITL: Prompt user interactively
      3. Save to .env for future sessions

    Returns:
        A list of valid API tokens.

    Raises:
        RuntimeError: If the user declines to provide a token.
    """
    env_var = _TOKEN_ENV_MAP.get(platform)
    if not env_var:
        raise ValueError(f"Unknown platform '{platform}'. Supported: {list(_TOKEN_ENV_MAP.keys())}")

    tokens = []
    
    # 1. Check environment for all variations
    for key, val in os.environ.items():
        if key == env_var or key.startswith(f"{env_var}_"):
            val = val.strip()
            if val and "your_" not in val:
                tokens.append(val)
                
    if tokens:
        print(f"  [ExternalService] ✓ Found {len(tokens)} {env_var}(s) in environment.")
        return tokens

    # 2. Check .env file directly (backup if dotenv wasn't loaded)
    if os.path.exists(_ENV_FILE):
        try:
            with open(_ENV_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith(env_var) and "=" in line:
                        val = line.split("=", 1)[1].strip().strip("'\"")
                        if val and "your_" not in val:
                            os.environ[line.split("=")[0]] = val
                            tokens.append(val)
            if tokens:
                print(f"  [ExternalService] ✓ Found {len(tokens)} {env_var}(s) in .env file.")
                return tokens
        except Exception:
            pass

    # 3. HITL: Ask the user
    print(f"\n  {'─'*58}")
    print(f"  [ExternalService] API token required for '{platform}'.")
    print(f"  The token will be saved to .env as {env_var} for future use.")
    print(f"  {'─'*58}")

    try:
        token = input(f"  Paste your {platform.upper()} API token: ").strip()
    except (EOFError, KeyboardInterrupt):
        raise RuntimeError(f"User declined to provide {env_var}. Cannot proceed.")

    if not token:
        raise RuntimeError(f"Empty token provided for {env_var}. Cannot proceed.")

    # 4. Save to .env in real-time
    _save_token_to_env(env_var, token)
    os.environ[env_var] = token
    print(f"  [ExternalService] ✓ Saved {env_var} to .env successfully.")

    return [token]


def _save_token_to_env(env_var: str, token: str) -> None:
    """
    Append or update a token in the .env file.
    If the variable already exists (with a placeholder), update it in-place.
    Otherwise, append it.
    """
    lines = []
    found = False

    if os.path.exists(_ENV_FILE):
        with open(_ENV_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()

    # Check if the variable already exists
    new_lines = []
    for line in lines:
        if line.strip().startswith(f"{env_var}="):
            new_lines.append(f"{env_var}={token}\n")
            found = True
        else:
            new_lines.append(line)

    if not found:
        # Ensure the file ends with a newline before appending
        if new_lines and not new_lines[-1].endswith("\n"):
            new_lines[-1] += "\n"
        new_lines.append(f"{env_var}={token}\n")

    with open(_ENV_FILE, "w", encoding="utf-8") as f:
        f.writelines(new_lines)

    # Reload dotenv so the change is immediately available
    try:
        from dotenv import load_dotenv
        load_dotenv(_ENV_FILE, override=True)
    except ImportError:
        pass


# ── Actor Catalog ──────────────────────────────────────────────────────────────

def _load_catalog(platform: str = "apify") -> dict:
    """
    Load the actor catalog for the given platform.
    Returns the 'actors' dict.
    """
    catalog_file = _CATALOG_FILES.get(platform)
    if not catalog_file:
        print(f"  [ExternalService] WARNING: No catalog file configured for platform '{platform}'")
        return {}

    if not os.path.exists(catalog_file):
        print(f"  [ExternalService] WARNING: Catalog file not found at {catalog_file}")
        return {}

    try:
        with open(catalog_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("actors", {})
    except Exception as e:
        print(f"  [ExternalService] WARNING: Failed to load catalog: {e}")
        return {}


def _select_actor(query: str, url: str = "", platform: str = "auto") -> dict:
    """
    Use the LLM to select the best platform and actor based on the user's query.
    Also streams its 'thinking' to the console.
    """
    platforms_to_check = ["apify", "brightdata"] if platform == "auto" else [platform]
    
    # Load combined catalog
    combined_catalog = {}
    for plat in platforms_to_check:
        plat_catalog = _load_catalog(plat)
        for key, actor in plat_catalog.items():
            # Prefix key with platform to avoid collisions
            combined_key = f"{plat}::{key}"
            actor["_platform"] = plat
            combined_catalog[combined_key] = actor
            
    if not combined_catalog:
        return {"error": "No actors available in catalog. Cannot proceed."}

    # Build menu
    menu_lines = []
    for key, actor in combined_catalog.items():
        menu_lines.append(
            f"- {key}: {actor['name']} ({actor['_platform']}) — {actor['description']} "
            f"(Use when: {actor.get('use_when', 'N/A')})"
        )
    menu_text = "\n".join(menu_lines)

    prompt = f"""You are a tool selector for an external scraping platform.

USER QUERY: "{query}"
USER URL: "{url or 'not provided'}"

AVAILABLE ACTORS:
{menu_text}

Pick the single best actor key from the list above.
1. First, provide a brief thought process in <thinking> tags explaining your choice.
2. Then, output ONLY a JSON object: {{"actor_key": "<key>"}}

Ensure the JSON is perfectly valid and follows the thinking block."""

    try:
        session = get_conversation_session(
            model=DEFAULT_MODEL,
            system_prompt="You select the best scraping actor. Output a <thinking> block then JSON."
        )
        
        # Stream the response so the user sees the thinking in real-time
        print(f"\n  [ExternalService] 🤔 Thinking:")
        response_text = session.chat(prompt, stream=True)
        print()

        # Parse the thinking block
        thinking_match = re.search(r"<thinking>([\s\S]*?)</thinking>", response_text)
        reasoning = thinking_match.group(1).strip() if thinking_match else "No reasoning provided."

        # Parse the JSON
        # Remove thinking block to find JSON
        json_str = re.sub(r"<thinking>[\s\S]*?</thinking>", "", response_text).strip()
        if json_str.startswith("```"):
            m = re.search(r"```(?:json)?\s*([\s\S]+?)\s*```", json_str)
            if m:
                json_str = m.group(1)

        result = json.loads(json_str)
        actor_key = result.get("actor_key", "")

        if actor_key in combined_catalog:
            selected = combined_catalog[actor_key].copy()
            selected["_catalog_key"] = actor_key.split("::")[1]
            selected["_selection_reasoning"] = reasoning
            print(f"  [ExternalService] ✓ Selected: {selected['name']} on {selected['_platform']}")
            return selected

    except Exception as e:
        print(f"  [ExternalService] Actor selection LLM failed: {e}")

    # Fallback: simple keyword matching if LLM fails
    best_key = list(combined_catalog.keys())[0]
    selected = combined_catalog[best_key].copy()
    selected["_catalog_key"] = best_key.split("::")[1]
    selected["_selection_reasoning"] = "Fallback chosen (LLM failed)"
    print(f"  [ExternalService] Fallback selected: {selected['name']} on {selected['_platform']}")
    return selected


# ── Build Actor Input ──────────────────────────────────────────────────────────

def _build_actor_input(
    actor: dict,
    query: str,
    url: str = "",
    max_items: int = 10,
) -> dict:
    """
    Build the actor's input payload using the template and the user's query/URL.

    Uses the LLM to intelligently fill in the template based on the user's
    query and the actor's input_notes.
    """
    template = actor.get("input_template", {})
    input_notes = actor.get("input_notes", "")
    catalog_key = actor.get("_catalog_key", "")

    # For actors with simple URL-based inputs, shortcut without LLM
    if url:
        if isinstance(template, list):
            # Bright Data style: [{"url": "<...>"}]
            filled_list = []
            for item in template:
                if isinstance(item, dict) and "url" in item:
                    filled_list.append({"url": url})
                else:
                    filled_list.append(item)
            return filled_list
            
        filled = {}
        for key, val in template.items():
            if isinstance(val, list) and len(val) == 1 and isinstance(val[0], str) and val[0].startswith("<"):
                # It's a placeholder URL list
                if isinstance(val[0], str) and "url" in key.lower():
                    filled[key] = [{"url": url}]
                else:
                    filled[key] = [url]
            elif isinstance(val, dict) and "url" in val:
                filled[key] = [{"url": url}]
            elif isinstance(val, str) and val.startswith("<"):
                filled[key] = query
            elif isinstance(val, int):
                # Max items override
                if "max" in key.lower() or "limit" in key.lower() or "result" in key.lower():
                    filled[key] = max_items
                else:
                    filled[key] = val
            else:
                filled[key] = val
        return filled

    # For keyword-based actors, use the LLM to fill the template
    prompt = f"""You are filling in an API input template for a web scraping actor.

ACTOR: {actor.get('name', 'Unknown')}
INPUT NOTES: {input_notes}
TEMPLATE: {json.dumps(template, indent=2)}

USER QUERY: "{query}"
MAX ITEMS: {max_items}

Replace all placeholder values (strings starting with <) with appropriate values based on the user's query.
Replace any max/limit integer fields with {max_items}.
Respond with ONLY the filled JSON object, no markdown, no explanation."""

    try:
        session = get_conversation_session(
            model=DEFAULT_MODEL,
            system_prompt="You fill in API input templates. Output ONLY valid JSON."
        )
        response = session.chat(prompt, format="json")
        response = response.strip()
        # Parse the JSON
        # Remove thinking block if present
        json_str = re.sub(r"<thinking>[\s\S]*?</thinking>", "", response).strip()
        if json_str.startswith("```"):
            m = re.search(r"```(?:json)?\s*([\s\S]+?)\s*```", json_str)
            if m:
                json_str = m.group(1)
        return json.loads(json_str)
    except Exception as e:
        print(f"  [ExternalService] Input builder LLM failed ({e}), using template defaults.")
        # Basic fallback
        if isinstance(template, list):
            filled_list = []
            for item in template:
                if isinstance(item, dict):
                    filled_item = {}
                    for k, v in item.items():
                        if isinstance(v, str) and v.startswith("<"):
                            filled_item[k] = query
                        else:
                            filled_item[k] = v
                    filled_list.append(filled_item)
                else:
                    filled_list.append(item)
            return filled_list
        else:
            filled = {}
            for key, val in template.items():
                if isinstance(val, list) and val and isinstance(val[0], str) and val[0].startswith("<"):
                    filled[key] = [query]
                elif isinstance(val, str) and val.startswith("<"):
                    filled[key] = query
                elif isinstance(val, int) and ("max" in key.lower() or "limit" in key.lower()):
                    filled[key] = max_items
                else:
                    filled[key] = val
            return filled


# ── Apify REST API Execution ──────────────────────────────────────────────────

def _run_apify_actor(actor_id: str, run_input: dict, tokens: list[str]) -> dict:
    """
    Execute an Apify actor via REST API with multi-key rotation.
    """
    print(f"  [ExternalService] Running Apify actor: {actor_id}")
    print(f"  [ExternalService] Input: {json.dumps(run_input, indent=2)[:300]}...")

    sync_url = f"{_APIFY_API_BASE}/acts/{actor_id}/run-sync-get-dataset-items"
    payload = json.dumps(run_input).encode("utf-8")

    last_error = ""

    for i, token in enumerate(tokens):
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type":  "application/json",
        }

        try:
            req = urllib.request.Request(sync_url, data=payload, headers=headers, method="POST")
            print(f"  [ExternalService] Calling Apify API (Key {i+1}/{len(tokens)})...")

            with urllib.request.urlopen(req, timeout=_SYNC_TIMEOUT) as resp:
                status = resp.status
                data = resp.read().decode("utf-8")

                if status in (200, 201):
                    items = json.loads(data)
                    if isinstance(items, list):
                        print(f"  [ExternalService] ✓ Received {len(items)} items from Apify.")
                        return {"success": True, "items": items, "run_id": "sync"}
                    elif isinstance(items, dict):
                        actual_items = items.get("items", items.get("data", [items]))
                        if not isinstance(actual_items, list):
                            actual_items = [actual_items]
                        return {"success": True, "items": actual_items, "run_id": "sync"}

        except urllib.error.HTTPError as e:
            error_body = ""
            try:
                error_body = e.read().decode("utf-8")[:300]
            except Exception:
                pass
                
            last_error = f"HTTP {e.code}: {e.reason} ({error_body})"
            
            # Rotate if rate limited or unauthorized
            if e.code in (401, 403, 429):
                print(f"  [ExternalService] ⚠️ Apify key failed ({e.code}). Rotating to next key...")
                continue
            else:
                break # Don't retry on other errors like 400 Bad Request

        except TimeoutError:
            print(f"  [ExternalService] Sync endpoint timed out. Falling back to async...")
            return _run_apify_actor_async(actor_id, run_input, token) # Fallback to async with current token

        except Exception as e:
            last_error = f"{type(e).__name__}: {e}"
            break

    return {
        "success": False,
        "items":   [],
        "error":   f"Apify API failed after trying {len(tokens)} key(s). Last error: {last_error}",
    }


def _run_apify_actor_async(actor_id: str, run_input: dict, token: str) -> dict:
    """
    Fallback: Run actor asynchronously and poll for results.
    """
    # 1. Start the run
    start_url = f"{_APIFY_API_BASE}/acts/{actor_id}/runs"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type":  "application/json",
    }
    payload = json.dumps(run_input).encode("utf-8")

    try:
        req = urllib.request.Request(start_url, data=payload, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=30) as resp:
            run_data = json.loads(resp.read().decode("utf-8"))

        run_id = run_data.get("data", {}).get("id", "")
        dataset_id = run_data.get("data", {}).get("defaultDatasetId", "")

        if not run_id:
            return {"success": False, "items": [], "error": "Failed to start async run."}

        print(f"  [ExternalService] Async run started: {run_id}")

    except Exception as e:
        return {"success": False, "items": [], "error": f"Failed to start async run: {e}"}

    # 2. Poll for completion (max 5 minutes)
    status_url = f"{_APIFY_API_BASE}/actor-runs/{run_id}"
    max_polls = 60  # 60 * 5s = 300s = 5 min
    for i in range(max_polls):
        time.sleep(5)
        try:
            req = urllib.request.Request(status_url, headers=headers)
            with urllib.request.urlopen(req, timeout=15) as resp:
                status_data = json.loads(resp.read().decode("utf-8"))

            run_status = status_data.get("data", {}).get("status", "")
            print(f"  [ExternalService] Poll {i+1}/{max_polls}: status={run_status}")

            if run_status in ("SUCCEEDED", "FINISHED"):
                break
            elif run_status in ("FAILED", "ABORTED", "TIMED-OUT"):
                return {
                    "success": False, "items": [],
                    "error": f"Apify run {run_status}: {status_data.get('data', {}).get('statusMessage', '')}",
                }
        except Exception:
            continue
    else:
        return {"success": False, "items": [], "error": "Async run polling timed out after 5 minutes."}

    # 3. Fetch dataset items
    if not dataset_id:
        dataset_id = status_data.get("data", {}).get("defaultDatasetId", "")

    if not dataset_id:
        return {"success": False, "items": [], "error": "No dataset ID found for completed run."}

    items_url = f"{_APIFY_API_BASE}/datasets/{dataset_id}/items?format=json"
    try:
        req = urllib.request.Request(items_url, headers=headers)
        with urllib.request.urlopen(req, timeout=60) as resp:
            items = json.loads(resp.read().decode("utf-8"))

        if isinstance(items, list):
            print(f"  [ExternalService] ✓ Fetched {len(items)} items from dataset.")
            return {"success": True, "items": items, "run_id": run_id}
        else:
            return {"success": True, "items": [items], "run_id": run_id}

    except Exception as e:
        return {"success": False, "items": [], "error": f"Failed to fetch dataset: {e}"}


# ── Bright Data REST API Execution ─────────────────────────────────────────────

def _run_brightdata_actor(dataset_id: str, run_input: list | dict, tokens: list[str]) -> dict:
    """
    Execute a Bright Data dataset scraper via REST API with multi-key rotation.
    """
    if isinstance(run_input, dict):
        run_input = [run_input]

    print(f"  [ExternalService] Running Bright Data scraper: {dataset_id}")
    print(f"  [ExternalService] Input ({len(run_input)} URLs): {json.dumps(run_input, indent=2)[:300]}...")

    sync_url = f"{_BRIGHTDATA_API_BASE}/scrape?dataset_id={dataset_id}&format=json"
    payload = json.dumps(run_input).encode("utf-8")
    
    last_error = ""

    for i, token in enumerate(tokens):
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type":  "application/json",
        }

        try:
            req = urllib.request.Request(sync_url, data=payload, headers=headers, method="POST")
            print(f"  [ExternalService] Calling Bright Data sync scrape (Key {i+1}/{len(tokens)})...")

            with urllib.request.urlopen(req, timeout=_SYNC_TIMEOUT) as resp:
                status = resp.status
                data = resp.read().decode("utf-8")

                if status in (200, 201):
                    items = json.loads(data)
                    if isinstance(items, list):
                        print(f"  [ExternalService] ✓ Received {len(items)} items from Bright Data (sync).")
                        return {"success": True, "items": items, "run_id": "sync"}
                    elif isinstance(items, dict):
                        actual = items.get("results", items.get("data", items.get("items", [items])))
                        if not isinstance(actual, list):
                            actual = [actual]
                        return {"success": True, "items": actual, "run_id": "sync"}
                        
        except urllib.error.HTTPError as e:
            error_body = ""
            try:
                error_body = e.read().decode("utf-8")[:300]
            except Exception:
                pass
                
            last_error = f"HTTP {e.code}: {e.reason} ({error_body})"
            
            # Rotate if rate limited or unauthorized
            if e.code in (401, 403, 429):
                print(f"  [ExternalService] ⚠️ Bright Data key failed ({e.code}). Rotating to next key...")
                continue
            elif e.code in (408, 504):
                print(f"  [ExternalService] Sync scrape timed out, falling back to async trigger...")
                return _run_brightdata_async(dataset_id, run_input, token, headers)
            else:
                break # Don't retry on other errors like 400 Bad Request
                
        except (TimeoutError, urllib.error.URLError) as e:
            print(f"  [ExternalService] Sync scrape timed out/failed, falling back to async...")
            return _run_brightdata_async(dataset_id, run_input, token, headers)

        except Exception as e:
            last_error = f"{type(e).__name__}: {e}"
            break

    return {
        "success": False,
        "items":   [],
        "error":   f"Bright Data API failed after trying {len(tokens)} key(s). Last error: {last_error}",
    }


def _run_brightdata_async(
    dataset_id: str, run_input: list, token: str, headers: dict
) -> dict:
    """
    Async fallback: trigger a Bright Data scrape job and poll for results.

    Flow:
      1. POST /datasets/v3/trigger?dataset_id=<ID> → get snapshot_id
      2. GET  /datasets/v3/progress/<snapshot_id>   → poll until ready
      3. GET  /datasets/v3/snapshot/<snapshot_id>?format=json → download items
    """
    # 1. Trigger
    trigger_url = f"{_BRIGHTDATA_API_BASE}/trigger?dataset_id={dataset_id}&format=json"
    payload = json.dumps(run_input).encode("utf-8")

    try:
        req = urllib.request.Request(trigger_url, data=payload, headers=headers, method="POST")
        print(f"  [ExternalService] Triggering Bright Data async job...")

        with urllib.request.urlopen(req, timeout=30) as resp:
            trigger_data = json.loads(resp.read().decode("utf-8"))

        snapshot_id = trigger_data.get("snapshot_id", "")
        if not snapshot_id:
            return {
                "success": False, "items": [],
                "error": f"Bright Data trigger returned no snapshot_id: {json.dumps(trigger_data)[:300]}",
            }

        print(f"  [ExternalService] Async job triggered. snapshot_id: {snapshot_id}")

    except Exception as e:
        return {"success": False, "items": [], "error": f"Failed to trigger Bright Data job: {e}"}

    # 2. Poll for completion (max 5 minutes, poll every 5 seconds)
    progress_url = f"{_BRIGHTDATA_API_BASE}/progress/{snapshot_id}"
    max_polls = 60
    for i in range(max_polls):
        time.sleep(5)
        try:
            req = urllib.request.Request(progress_url, headers=headers)
            with urllib.request.urlopen(req, timeout=15) as resp:
                progress = json.loads(resp.read().decode("utf-8"))

            status = progress.get("status", "")
            print(f"  [ExternalService] Poll {i+1}/{max_polls}: status={status}")

            if status in ("ready", "completed", "succeeded"):
                break
            elif status in ("failed", "error"):
                return {
                    "success": False, "items": [],
                    "error": f"Bright Data job failed: {progress.get('message', status)}",
                }
        except Exception:
            continue
    else:
        return {"success": False, "items": [], "error": "Bright Data async polling timed out (5 min)."}

    # 3. Download results
    snapshot_url = f"{_BRIGHTDATA_API_BASE}/snapshot/{snapshot_id}?format=json"
    try:
        req = urllib.request.Request(snapshot_url, headers=headers)
        with urllib.request.urlopen(req, timeout=60) as resp:
            items = json.loads(resp.read().decode("utf-8"))

        if isinstance(items, list):
            print(f"  [ExternalService] ✓ Downloaded {len(items)} items from Bright Data snapshot.")
            return {"success": True, "items": items, "run_id": snapshot_id}
        else:
            return {"success": True, "items": [items], "run_id": snapshot_id}

    except Exception as e:
        return {"success": False, "items": [], "error": f"Failed to download Bright Data snapshot: {e}"}


# ── Data Persistence ──────────────────────────────────────────────────────────

def _save_results(
    items: list,
    actor_name: str,
    catalog_key: str,
    platform: str,
    query: str,
    url: str,
    run_id: str,
) -> str:
    """
    Save scraped results to external_data/<platform>/<descriptive_name>_<timestamp>.json.
    Also appends a log entry to external_data/logs/request_log.jsonl.

    Returns the filepath of the saved data.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_key = re.sub(r"[^a-zA-Z0-9_]", "_", catalog_key)

    # Save data file
    platform_dir = os.path.join(_DATA_ROOT, platform)
    os.makedirs(platform_dir, exist_ok=True)

    filename = f"{safe_key}_{timestamp}.json"
    filepath = os.path.join(platform_dir, filename)

    save_payload = {
        "metadata": {
            "actor_name":  actor_name,
            "catalog_key": catalog_key,
            "platform":    platform,
            "query":       query,
            "url":         url,
            "run_id":      run_id,
            "item_count":  len(items),
            "fetched_at":  datetime.now().isoformat(),
        },
        "items": items,
    }

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(save_payload, f, indent=2, ensure_ascii=False)

    print(f"  [ExternalService] ✓ Data saved to: {filepath}")

    # Append to request log
    os.makedirs(os.path.dirname(_LOG_FILE), exist_ok=True)
    log_entry = {
        "timestamp":   datetime.now().isoformat(),
        "platform":    platform,
        "actor_name":  actor_name,
        "catalog_key": catalog_key,
        "query":       query,
        "url":         url,
        "item_count":  len(items),
        "data_file":   filepath,
        "run_id":      run_id,
    }

    try:
        with open(_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
    except Exception:
        pass  # Logging failure shouldn't crash the agent

    return filepath


# ── Primary Function ───────────────────────────────────────────────────────────

def external_service_agent(
    query: str,
    url: str = "",
    platform: str = "auto",
    max_items: int = 10,
) -> dict:
    """
    Main entry point for the external service agent.
    """
    platform = platform.lower().strip()
    print(f"\n  [ExternalService] ═══════════════════════════════════════")
    print(f"  [ExternalService] Query: {query[:100]}")
    print(f"  [ExternalService] URL: {url or '(none)'}")
    print(f"  [ExternalService] Platform: {platform}")
    print(f"  [ExternalService] Max items: {max_items}")
    print(f"  [ExternalService] ═══════════════════════════════════════\n")

    # ── Step 1: Select actor & platform ──────────────────────────────
    actor = _select_actor(query, url, platform)

    if "error" in actor:
        return {"status": "error", "error": actor["error"]}

    selected_platform = actor.get("_platform", platform)
    actor_id = actor.get("actor_id", "") or actor.get("dataset_id", "")
    actor_name = actor.get("name", "Unknown")
    catalog_key = actor.get("_catalog_key", "unknown")

    if not actor_id:
        return {"status": "error", "error": "Selected actor has no actor_id/dataset_id."}

    # ── Step 2: Token ────────────────────────────────────────────────
    try:
        tokens = _resolve_tokens(selected_platform)
    except (RuntimeError, ValueError) as e:
        return {"status": "error", "error": str(e)}

    # ── Step 3: Build input ──────────────────────────────────────────
    run_input = _build_actor_input(actor, query, url, max_items)
    print(f"  [ExternalService] Built input: {json.dumps(run_input, indent=2)[:400]}")

    # ── Step 4: Execute ──────────────────────────────────────────────
    if selected_platform == "apify":
        result = _run_apify_actor(actor_id, run_input, tokens)
    elif selected_platform == "brightdata":
        result = _run_brightdata_actor(actor_id, run_input, tokens)
    else:
        return {
            "status": "error",
            "error":  f"Platform '{selected_platform}' is not supported.",
        }

    if not result.get("success"):
        return {
            "status":     "error",
            "platform":   platform,
            "actor_name": actor_name,
            "error":      result.get("error", "Unknown error from external API."),
        }

    items = result.get("items", [])
    run_id = result.get("run_id", "")

    if not items:
        return {
            "status":     "error",
            "platform":   platform,
            "actor_name": actor_name,
            "error":      "Actor completed but returned 0 items.",
        }

    # ── Step 5: Save ─────────────────────────────────────────────────
    filepath = _save_results(
        items=items,
        actor_name=actor_name,
        catalog_key=catalog_key,
        platform=platform,
        query=query,
        url=url,
        run_id=run_id,
    )

    # ── Step 6: Return ───────────────────────────────────────────────
    # Truncate items for orchestrator context (full data is in the saved file)
    display_items = items[:5] if len(items) > 5 else items

    return {
        "status":       "success",
        "platform":     platform,
        "actor_name":   actor_name,
        "item_count":   len(items),
        "saved_to":     filepath,
        "text":         json.dumps(display_items, indent=2, ensure_ascii=False),
        "data":         display_items,
        "_full_data_file": filepath,
    }
