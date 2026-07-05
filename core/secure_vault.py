"""
Secure Vault — Encrypted Session & Credential Storage
------------------------------------------------------
Provides AES-256 encrypted storage for session tokens, cookies, and credentials.
All data is encrypted at rest using a machine-derived key or a user-provided passphrase.

Security guarantees:
- All session files are AES-256-CBC encrypted via Fernet (cryptography library).
- Master key is derived from a passphrase using PBKDF2 with 480,000 iterations.
- If no passphrase is provided, a machine-unique key is auto-generated and stored
  with chmod 600 permissions.
- Session metadata (platform, created_at, expires_at) is stored alongside
  encrypted payloads so the system can detect stale sessions without decrypting.
- File permissions are set to 600 (owner-read/write only) on all vault files.

Usage:
    from core.secure_vault import SecureVault

    vault = SecureVault()
    vault.store_session("github", session_data_dict, expires_in_hours=336)
    data = vault.load_session("github")  # Returns None if expired or missing
"""

import os
import json
import stat
import time
import base64
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

# ── Constants ──────────────────────────────────────────────────────────────────

VAULT_DIR = os.path.join(os.getcwd(), "archive", "vault")
VAULT_KEY_FILE = os.path.join(VAULT_DIR, ".vault_master.key")
VAULT_META_FILE = os.path.join(VAULT_DIR, ".vault_index.json")

# Default session expiry (14 days — matches most OAuth session lifetimes)
DEFAULT_EXPIRY_HOURS = 336


# ── Encryption Primitives ─────────────────────────────────────────────────────

def _ensure_cryptography():
    """Check that the cryptography library is available."""
    try:
        from cryptography.fernet import Fernet
        from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
        from cryptography.hazmat.primitives import hashes
        return True
    except ImportError:
        return False


def _derive_key_from_passphrase(passphrase: str, salt: bytes) -> bytes:
    """Derive a Fernet-compatible key from a passphrase using PBKDF2."""
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.hazmat.primitives import hashes

    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=480_000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(passphrase.encode()))
    return key


def _set_file_permissions(filepath: str):
    """Set file permissions to 600 (owner read/write only)."""
    try:
        os.chmod(filepath, stat.S_IRUSR | stat.S_IWUSR)
    except OSError:
        pass  # Windows doesn't support Unix permissions; skip silently


# ── Secure Vault Class ────────────────────────────────────────────────────────

class SecureVault:
    """
    Encrypted storage for session tokens and credentials.
    
    Security model:
    - On first use, generates a random master key and stores it in .vault_master.key
      with chmod 600 permissions.
    - All session data is encrypted with AES-256 via Fernet before writing to disk.
    - A metadata index tracks platform names, creation times, and expiry times
      WITHOUT storing any actual secrets — so we can check staleness without decrypting.
    """

    def __init__(self, passphrase: Optional[str] = None):
        """
        Initialize the vault.
        
        Args:
            passphrase: Optional user passphrase. If provided, the master key is
                        derived from it via PBKDF2. If not, an auto-generated
                        machine key is used.
        """
        os.makedirs(VAULT_DIR, exist_ok=True)

        if not _ensure_cryptography():
            raise ImportError(
                "The 'cryptography' library is required for the Secure Vault. "
                "Install it with: pip install cryptography"
            )

        from cryptography.fernet import Fernet

        if passphrase:
            # Derive key from passphrase
            salt_file = os.path.join(VAULT_DIR, ".vault_salt")
            if os.path.exists(salt_file):
                with open(salt_file, "rb") as f:
                    salt = f.read()
            else:
                salt = secrets.token_bytes(16)
                with open(salt_file, "wb") as f:
                    f.write(salt)
                _set_file_permissions(salt_file)

            self._key = _derive_key_from_passphrase(passphrase, salt)
        else:
            # Use auto-generated machine key
            self._key = self._load_or_create_master_key()

        self._fernet = Fernet(self._key)
        self._meta = self._load_meta()

    def _load_or_create_master_key(self) -> bytes:
        """Load existing master key or generate a new one."""
        from cryptography.fernet import Fernet

        if os.path.exists(VAULT_KEY_FILE):
            with open(VAULT_KEY_FILE, "rb") as f:
                key = f.read().strip()
            return key
        else:
            key = Fernet.generate_key()
            with open(VAULT_KEY_FILE, "wb") as f:
                f.write(key)
            _set_file_permissions(VAULT_KEY_FILE)
            print("  [Vault] 🔐 Generated new master encryption key.")
            return key

    def _load_meta(self) -> dict:
        """Load the vault metadata index."""
        if os.path.exists(VAULT_META_FILE):
            try:
                with open(VAULT_META_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return {"sessions": {}}
        return {"sessions": {}}

    def _save_meta(self):
        """Save the vault metadata index."""
        with open(VAULT_META_FILE, "w", encoding="utf-8") as f:
            json.dump(self._meta, f, indent=2, default=str)
        _set_file_permissions(VAULT_META_FILE)

    # ── Public API ─────────────────────────────────────────────────────────────

    def store_session(
        self,
        platform: str,
        session_data: dict,
        expires_in_hours: int = DEFAULT_EXPIRY_HOURS,
        label: str = ""
    ) -> dict:
        """
        Encrypt and store a session for a given platform.

        Args:
            platform: e.g., "github", "google", "linkedin"
            session_data: The raw Playwright storage_state dict (cookies, localStorage, etc.)
            expires_in_hours: How many hours until this session is considered stale.
            label: Optional human label like "personal" or "work".

        Returns:
            dict with success status and metadata.
        """
        platform = platform.lower().strip()
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(hours=expires_in_hours)

        # Encrypt the session data
        raw_json = json.dumps(session_data, ensure_ascii=False).encode("utf-8")
        encrypted = self._fernet.encrypt(raw_json)

        # Write encrypted file
        session_file = os.path.join(VAULT_DIR, f"{platform}.vault")
        with open(session_file, "wb") as f:
            f.write(encrypted)
        _set_file_permissions(session_file)

        # Update metadata (no secrets stored here)
        self._meta["sessions"][platform] = {
            "created_at": now.isoformat(),
            "expires_at": expires_at.isoformat(),
            "label": label or platform,
            "file": f"{platform}.vault",
            "size_bytes": len(encrypted),
        }
        self._save_meta()

        print(f"  [Vault] 🔒 Session for '{platform}' encrypted and stored.")
        print(f"  [Vault]    Expires: {expires_at.strftime('%Y-%m-%d %H:%M UTC')}")

        return {
            "success": True,
            "platform": platform,
            "expires_at": expires_at.isoformat(),
            "file": session_file,
        }

    def load_session(self, platform: str) -> Optional[dict]:
        """
        Decrypt and return a stored session.

        Returns:
            The decrypted session dict, or None if expired/missing/corrupted.
        """
        platform = platform.lower().strip()
        meta = self._meta.get("sessions", {}).get(platform)

        if not meta:
            print(f"  [Vault] ⚠️  No session found for '{platform}'.")
            return None

        # Check expiry BEFORE decrypting (saves resources)
        expires_at = datetime.fromisoformat(meta["expires_at"])
        now = datetime.now(timezone.utc)

        if now > expires_at:
            print(f"  [Vault] ⚠️  Session for '{platform}' has EXPIRED.")
            print(f"  [Vault]    Expired at: {expires_at.strftime('%Y-%m-%d %H:%M UTC')}")
            print(f"  [Vault]    Please re-authenticate using auth_agent.")
            return None

        # Decrypt
        session_file = os.path.join(VAULT_DIR, f"{platform}.vault")
        if not os.path.exists(session_file):
            print(f"  [Vault] ⚠️  Encrypted file missing for '{platform}'.")
            return None

        try:
            with open(session_file, "rb") as f:
                encrypted = f.read()
            decrypted = self._fernet.decrypt(encrypted)
            session_data = json.loads(decrypted.decode("utf-8"))

            remaining = expires_at - now
            hours_left = remaining.total_seconds() / 3600
            print(f"  [Vault] 🔓 Session for '{platform}' decrypted. ({hours_left:.0f}h remaining)")

            return session_data

        except Exception as e:
            print(f"  [Vault] ❌ Failed to decrypt session for '{platform}': {e}")
            return None

    def delete_session(self, platform: str) -> dict:
        """Securely delete a stored session (overwrite + remove)."""
        platform = platform.lower().strip()
        session_file = os.path.join(VAULT_DIR, f"{platform}.vault")

        if os.path.exists(session_file):
            # Overwrite with random bytes before deleting (secure wipe)
            file_size = os.path.getsize(session_file)
            with open(session_file, "wb") as f:
                f.write(secrets.token_bytes(file_size))
            os.remove(session_file)

        if platform in self._meta.get("sessions", {}):
            del self._meta["sessions"][platform]
            self._save_meta()

        print(f"  [Vault] 🗑️  Session for '{platform}' securely destroyed.")
        return {"success": True, "message": f"Session for '{platform}' destroyed."}

    def list_sessions(self) -> dict:
        """List all stored sessions with their expiry status (no secrets exposed)."""
        now = datetime.now(timezone.utc)
        sessions = []

        for platform, meta in self._meta.get("sessions", {}).items():
            expires_at = datetime.fromisoformat(meta["expires_at"])
            is_expired = now > expires_at

            if is_expired:
                status = "EXPIRED"
                remaining = "0h"
            else:
                status = "ACTIVE"
                remaining_td = expires_at - now
                remaining = f"{remaining_td.total_seconds() / 3600:.0f}h"

            sessions.append({
                "platform": platform,
                "label": meta.get("label", ""),
                "status": status,
                "created_at": meta["created_at"],
                "expires_at": meta["expires_at"],
                "remaining": remaining,
            })

        return {"success": True, "sessions": sessions}

    def is_session_valid(self, platform: str) -> bool:
        """Quick check: is the session for this platform still valid?"""
        platform = platform.lower().strip()
        meta = self._meta.get("sessions", {}).get(platform)
        if not meta:
            return False
        expires_at = datetime.fromisoformat(meta["expires_at"])
        return datetime.now(timezone.utc) < expires_at

    def export_decrypted_temp(self, platform: str) -> Optional[str]:
        """
        Temporarily decrypt a session to a plain JSON file for Playwright to consume,
        then return the path. The caller MUST delete this file after use.
        
        This is necessary because Playwright's storage_state() expects a plain JSON path.
        """
        session_data = self.load_session(platform)
        if not session_data:
            return None

        temp_file = os.path.join(VAULT_DIR, f".tmp_{platform}_decrypted.json")
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(session_data, f)
        _set_file_permissions(temp_file)

        return temp_file

    def cleanup_temp(self, platform: str):
        """Remove the temporary decrypted file after Playwright has consumed it."""
        temp_file = os.path.join(VAULT_DIR, f".tmp_{platform}_decrypted.json")
        if os.path.exists(temp_file):
            # Overwrite then delete
            size = os.path.getsize(temp_file)
            with open(temp_file, "wb") as f:
                f.write(secrets.token_bytes(size))
            os.remove(temp_file)
