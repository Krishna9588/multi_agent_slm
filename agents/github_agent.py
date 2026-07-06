"""
Agent: github_agent
-------------------
The Software Engineer Agent. 
Interacts with Git and GitHub via the CLI to clone repos, branch, and commit.
"""

import os
import subprocess

DESCRIPTION = (
    "The Software Engineer Agent. Use this to clone GitHub repositories, create branches, "
    "and commit changes locally. It operates strictly within the 'archive/github_repos/' sandbox."
)

PARAMETERS = {
    "action": {
        "type": "string",
        "required": True,
        "description": "Must be one of: 'clone_repo', 'create_branch', 'commit_changes'.",
    },
    "repo_url": {
        "type": "string",
        "required": False,
        "description": "The GitHub repository URL (required for clone_repo).",
    },
    "repo_name": {
        "type": "string",
        "required": False,
        "description": "The local name of the repo (required for branch/commit actions).",
    },
    "branch_name": {
        "type": "string",
        "required": False,
        "description": "The name of the new branch (required for create_branch).",
    },
    "commit_message": {
        "type": "string",
        "required": False,
        "description": "The commit message (required for commit_changes).",
    }
}

# Jailed sandbox for all git operations
SANDBOX_DIR = os.path.join(os.getcwd(), "archive", "github_repos")

def _run_git(command: list, cwd: str = SANDBOX_DIR) -> dict:
    try:
        os.makedirs(cwd, exist_ok=True)
        result = subprocess.run(["git"] + command, cwd=cwd, capture_output=True, text=True, check=True)
        return {"success": True, "output": result.stdout.strip()}
    except subprocess.CalledProcessError as e:
        # Check for merge conflicts or specific git errors
        error_msg = e.stderr.strip()
        if "CONFLICT" in error_msg:
            return {"error": f"Merge conflict detected: {error_msg}. Manual intervention required."}
        return {"error": f"Git command failed: {error_msg}"}
    except Exception as e:
        return {"error": str(e)}

def github_agent(
    action: str, 
    repo_url: str = "", 
    repo_name: str = "", 
    branch_name: str = "", 
    commit_message: str = ""
) -> dict:
    """Interacts with local git repositories."""
    action = action.lower().strip()
    
    if action == "clone_repo":
        if not repo_url:
            return {"error": "clone_repo requires 'repo_url'."}
            
        # Extract repo name from URL
        extracted_name = repo_url.rstrip('/').split('/')[-1]
        if extracted_name.endswith('.git'):
            extracted_name = extracted_name[:-4]
            
        repo_dir = os.path.join(SANDBOX_DIR, extracted_name)
        if os.path.exists(repo_dir):
            return {"success": True, "message": f"Repository '{extracted_name}' is already cloned in the sandbox."}
            
        # Optional: Auth using GITHUB_TOKEN from env if needed for private repos
        print(f"  [GitHub] Cloning {repo_url} into {SANDBOX_DIR}...")
        return _run_git(["clone", repo_url])
        
    elif action == "create_branch":
        if not repo_name or not branch_name:
            return {"error": "create_branch requires 'repo_name' and 'branch_name'."}
            
        repo_dir = os.path.join(SANDBOX_DIR, repo_name)
        if not os.path.exists(repo_dir):
            return {"error": f"Repository '{repo_name}' not found in sandbox."}
            
        print(f"  [GitHub] Creating branch {branch_name} in {repo_name}...")
        return _run_git(["checkout", "-b", branch_name], cwd=repo_dir)
        
    elif action == "commit_changes":
        if not repo_name or not commit_message:
            return {"error": "commit_changes requires 'repo_name' and 'commit_message'."}
            
        repo_dir = os.path.join(SANDBOX_DIR, repo_name)
        if not os.path.exists(repo_dir):
            return {"error": f"Repository '{repo_name}' not found in sandbox."}
            
        print(f"  [GitHub] Committing changes to {repo_name}...")
        # Add all and commit
        add_result = _run_git(["add", "."], cwd=repo_dir)
        if "error" in add_result:
            return add_result
            
        commit_result = _run_git(["commit", "-m", commit_message], cwd=repo_dir)
        
        # If nothing to commit, git returns an error code sometimes, handle cleanly:
        if "error" in commit_result and "nothing to commit" in commit_result["error"]:
            return {"success": True, "message": "Nothing to commit. Working tree clean."}
            
        return commit_result
        
    else:
        return {"error": "Invalid action. Use 'clone_repo', 'create_branch', or 'commit_changes'."}
