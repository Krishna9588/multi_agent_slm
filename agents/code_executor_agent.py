"""
Agent: code_executor_agent
--------------------------
Provides a sandboxed Python execution environment.
Allows the LLM to write and execute arbitrary Python code to analyze data,
test logic, or run newly created scripts.

Safety: Runs in a separate subprocess with a strict timeout.
"""

import subprocess
import tempfile
import os
import sys

DESCRIPTION = (
    "Execute Python code in a secure, isolated local subprocess. "
    "Use this to perform complex calculations, test algorithms, or run dynamic scripts. "
    "The code is executed and the standard output (print statements) and errors are returned. "
    "You must use 'print()' in your code to output the results you want to see."
)

PARAMETERS = {
    "code": {
        "type": "string",
        "required": True,
        "description": "The Python code to execute. Must be valid Python 3 code.",
    },
    "timeout_seconds": {
        "type": "integer",
        "required": False,
        "description": "Maximum execution time in seconds. Defaults to 30.",
    }
}

def code_executor_agent(code: str, timeout_seconds: int = 30) -> dict:
    """Executes python code and returns the output."""
    if not code or not code.strip():
        return {"error": "No code provided to execute."}

    # Write code to a temporary file
    fd, path = tempfile.mkstemp(suffix=".py", text=True)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            f.write(code)
            
        # Execute the temporary file inside an isolated Docker container
        try:
            # -i: interactive (keeps stdin open)
            # --rm: removes container after execution
            # --network none: disables internet access for maximum security
            # -v: mount the script into the container
            docker_cmd = [
                "docker", "run", "--rm",
                "--network", "none",
                "-v", f"{path}:/script.py:ro",
                "python:3.10-slim",
                "python", "/script.py"
            ]
            
            result = subprocess.run(
                docker_cmd,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                encoding='utf-8',
                errors='replace'
            )
            
            return {
                "stdout": result.stdout.strip(),
                "stderr": result.stderr.strip(),
                "exit_code": result.returncode
            }
            
        except subprocess.TimeoutExpired:
            return {
                "error": f"Execution timed out after {timeout_seconds} seconds.",
                "stdout": "",
                "stderr": "",
                "exit_code": -1
            }
        except Exception as e:
            error_msg = str(e)
            if "failed to connect to the docker API" in error_msg or "docker.sock" in error_msg:
                return {"error": "Docker is not running. Please start Docker Desktop to use the code_executor_agent.", "details": error_msg}
            return {"error": f"Failed to execute code: {error_msg}", "exit_code": -1}
            
    finally:
        # Always clean up the temporary file
        try:
            os.remove(path)
        except OSError:
            pass
