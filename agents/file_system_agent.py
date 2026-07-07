"""
Agent: file_system_agent
------------------------
The Organizer Agent. Safely navigates the local file system.
CRITICAL SAFETY: This agent is strictly jailed to the 'archive/workspace' directory.
It cannot access, read, or delete files outside this folder to protect the host OS.
"""

import os
import shutil
import glob

DESCRIPTION = (
    "The Organizer Agent. Use this to safely organize, move, search, or compress files. "
    "To prevent accidental damage to the computer, you are strictly jailed to the 'archive/workspace' directory. "
    "You cannot access files outside this sandbox."
)

PARAMETERS = {
    "action": {
        "type": "string",
        "required": True,
        "description": "Must be one of: 'search_files', 'move_file', 'compress_folder'.",
    },
    "pattern_or_source": {
        "type": "string",
        "required": True,
        "description": "The search pattern (e.g. '*.csv') or the source file path to move/compress.",
    },
    "destination": {
        "type": "string",
        "required": False,
        "description": "The destination path (required for move_file).",
    }
}

# The Sandbox Jail
JAIL_DIR = os.path.abspath(os.path.join(os.getcwd(), "archive", "workspace"))
os.makedirs(JAIL_DIR, exist_ok=True)

def _is_safe_path(target_path: str) -> bool:
    """Ensures the target path resolves inside the JAIL_DIR."""
    abs_target = os.path.abspath(os.path.join(JAIL_DIR, target_path))
    return abs_target.startswith(JAIL_DIR)

def _get_safe_path(target_path: str) -> str:
    abs_target = os.path.abspath(os.path.join(JAIL_DIR, target_path))
    if not abs_target.startswith(JAIL_DIR):
        raise PermissionError(f"SECURITY BLOCK: Attempted path traversal outside of sandbox ({target_path})")
    return abs_target

def file_system_agent(
    action: str, 
    pattern_or_source: str, 
    destination: str = ""
) -> dict:
    """Interacts safely with the file system."""
    action = action.lower().strip()
    
    try:
        if action == "search_files":
            # pattern_or_source is a glob pattern
            # Force search to be relative to JAIL_DIR
            safe_pattern = os.path.join(JAIL_DIR, "**", pattern_or_source)
            
            # recursive=True allows searching in subdirectories
            matches = glob.glob(safe_pattern, recursive=True)
            
            # Make paths relative for the LLM so it doesn't see our absolute system paths
            relative_matches = [os.path.relpath(m, JAIL_DIR) for m in matches]
            
            if not relative_matches:
                return {"success": True, "message": f"No files found matching '{pattern_or_source}'."}
                
            return {"success": True, "matches": relative_matches[:50]} # Cap at 50
            
        elif action == "move_file":
            if not destination:
                return {"error": "move_file requires a 'destination'."}
                
            safe_src = _get_safe_path(pattern_or_source)
            safe_dest = _get_safe_path(destination)
            
            if not os.path.exists(safe_src):
                return {"error": f"Source file '{pattern_or_source}' not found."}
                
            os.makedirs(os.path.dirname(safe_dest), exist_ok=True)
            shutil.move(safe_src, safe_dest)
            
            return {"success": True, "message": f"Successfully moved to {destination}."}
            
        elif action == "compress_folder":
            safe_src = _get_safe_path(pattern_or_source)
            
            if not os.path.isdir(safe_src):
                return {"error": f"'{pattern_or_source}' is not a directory."}
                
            # Compress it to the same parent directory with .zip
            archive_name = shutil.make_archive(safe_src, 'zip', safe_src)
            rel_archive = os.path.relpath(archive_name, JAIL_DIR)
            
            return {"success": True, "message": f"Successfully compressed folder into {rel_archive}."}
            
        else:
            return {"error": "Invalid action. Use 'search_files', 'move_file', or 'compress_folder'."}
            
    except PermissionError as e:
        return {"error": str(e)}
    except Exception as e:
        return {"error": f"File system operation failed: {str(e)}"}
