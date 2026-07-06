import os
import re

agent_files = [f for f in os.listdir("agents") if f.endswith(".py") and not f.startswith("_")]
info = {}

for f in agent_files:
    if f in ["schemas.py", "setup_guide_agent.py", "test_tool.py"]: continue
    path = os.path.join("agents", f)
    with open(path, "r") as file:
        content = file.read()
        desc_match = re.search(r'DESCRIPTION\s*=\s*(?:\(\s*)?["\'](.*?)["\']', content, re.DOTALL)
        if desc_match:
            desc = desc_match.group(1).replace('\n', ' ').strip()
            info[f] = desc

for k, v in info.items():
    print(f"--- {k} ---")
    print(v[:200] + "...")
