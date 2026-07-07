"""
Agent: auth_agent
-----------------
Specialized agent for handling authentication flows (logins).
Uses Playwright to open a visible browser for the user to log in manually,
then encrypts and stores the session in the Secure Vault.

Security:
- Sessions are AES-256 encrypted at rest (never stored as plain JSON).
- Expired sessions are detected and the user is prompted to re-authenticate.
- Temporary decrypted files are securely wiped after Playwright consumes them.
"""

import os

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright = None

from core.secure_vault import SecureVault

DESCRIPTION = (
    "An Interactive Authentication Agent. Use this when the Swarm hits a login wall or 401 error. "
    "Actions: 'login' to authenticate, 'check' to verify a session is still valid, "
    "'list' to see all stored sessions, 'logout' to securely destroy a session. "
    "Supported platforms: 'linkedin', 'github', 'google', 'twitter', or any custom URL. "
    "Sessions are AES-256 encrypted at rest and automatically expire after 14 days."
)

PARAMETERS = {
    "action": {
        "type": "string",
        "required": True,
        "description": "Must be one of: 'login', 'check', 'list', 'logout'.",
    },
    "platform": {
        "type": "string",
        "required": False,
        "description": "The platform to authenticate with (e.g., 'github', 'google', 'linkedin').",
    },
    "login_url": {
        "type": "string",
        "required": False,
        "description": "The exact URL of the login page (required for 'login' action).",
    },
    "expires_in_hours": {
        "type": "integer",
        "required": False,
        "description": "Custom session expiry in hours (default: 336 = 14 days).",
    },
}

# ── Platform URL defaults ──────────────────────────────────────────────────────
PLATFORM_URLS = {
    "github": "https://github.com/login",
    "google": "https://accounts.google.com/",
    "linkedin": "https://www.linkedin.com/login",
    "twitter": "https://x.com/i/flow/login",
}

# ── Session expiry defaults (hours) ───────────────────────────────────────────
PLATFORM_EXPIRY = {
    "github": 336,     # 14 days
    "google": 720,     # 30 days (Google sessions last longer)
    "linkedin": 168,   # 7 days (LinkedIn is aggressive with session invalidation)
    "twitter": 720,    # 30 days
}


def auth_agent(
    action: str,
    platform: str = "",
    login_url: str = "",
    expires_in_hours: int = 0,
) -> dict:
    """Manages encrypted authentication sessions for the Swarm."""
    action = action.lower().strip()

    try:
        vault = SecureVault()
    except ImportError as e:
        return {"error": str(e)}

    # ── ACTION: list ───────────────────────────────────────────────────────
    if action == "list":
        return vault.list_sessions()

    # ── ACTION: check ──────────────────────────────────────────────────────
    if action == "check":
        if not platform:
            return {"error": "'check' requires a 'platform' name."}
        is_valid = vault.is_session_valid(platform)
        if is_valid:
            meta = vault._meta.get("sessions", {}).get(platform.lower(), {})
            return {
                "success": True,
                "platform": platform,
                "status": "ACTIVE",
                "expires_at": meta.get("expires_at", "unknown"),
                "message": f"Session for '{platform}' is valid and encrypted.",
            }
        else:
            return {
                "success": True,
                "platform": platform,
                "status": "EXPIRED_OR_MISSING",
                "message": f"No valid session for '{platform}'. Re-authenticate with action='login'.",
            }

    # ── ACTION: logout ─────────────────────────────────────────────────────
    if action == "logout":
        if not platform:
            return {"error": "'logout' requires a 'platform' name."}
        return vault.delete_session(platform)

    # ── ACTION: login ──────────────────────────────────────────────────────
    if action == "login":
        if sync_playwright is None:
            return {
                "error": "Playwright is not installed. "
                "Run: pip install playwright && playwright install"
            }
        if not platform:
            return {"error": "'login' requires a 'platform' name."}

        # Resolve the login URL
        platform_key = platform.lower().strip()
        if not login_url:
            login_url = PLATFORM_URLS.get(platform_key)
            if not login_url:
                return {
                    "error": f"No default login URL for '{platform}'. "
                    f"Please provide one via 'login_url'."
                }

        # Resolve expiry
        if expires_in_hours <= 0:
            expires_in_hours = PLATFORM_EXPIRY.get(platform_key, 336)

        # Check if we already have a valid session
        if vault.is_session_valid(platform_key):
            meta = vault._meta.get("sessions", {}).get(platform_key, {})
            return {
                "success": True,
                "message": f"Session for '{platform}' is still active. "
                f"Expires at {meta.get('expires_at', 'unknown')}. "
                f"Use action='logout' first if you want to re-authenticate.",
                "status": "ALREADY_AUTHENTICATED",
            }

        # Open the browser for interactive login
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=False)
                context = browser.new_context()
                page = context.new_page()

                print(f"\n  [AuthAgent] 🔐 INTERACTIVE LOGIN — {platform.upper()}")
                print(f"  [AuthAgent] Opening: {login_url}")
                print(f"  [AuthAgent] Please log in manually (2FA, OAuth, etc.).")
                print(f"  [AuthAgent] The session will be encrypted and stored for {expires_in_hours}h.\n")

                page.goto(login_url, wait_until="domcontentloaded")

                # Wait for user to finish
                try:
                    input("  [AuthAgent] Press ENTER here once you have logged in... ")
                except (EOFError, KeyboardInterrupt):
                    browser.close()
                    return {"error": "Authentication cancelled by user."}

                # Capture the full browser state
                session_data = context.storage_state()
                browser.close()

            # Encrypt and store via the vault
            result = vault.store_session(
                platform=platform_key,
                session_data=session_data,
                expires_in_hours=expires_in_hours,
                label=platform,
            )

            return {
                "success": True,
                "message": f"Session for '{platform}' authenticated, encrypted, and stored.",
                "expires_at": result["expires_at"],
                "security": "AES-256 encrypted at rest. File permissions: 600 (owner-only).",
            }

        except Exception as e:
            return {"error": f"Interactive authentication failed: {str(e)}"}

    return {"error": f"Unknown action '{action}'. Must be: login, check, list, logout."}
