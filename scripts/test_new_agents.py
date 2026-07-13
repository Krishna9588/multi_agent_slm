import json
from agents.finance_agent import finance_agent
from agents.pentest_agent import pentest_agent
from agents.contract_analysis_agent import contract_analysis_agent
from agents.data_science_agent import data_science_agent

print("--- 1. FINANCE AGENT SCRIPT TEST ---")
res1 = finance_agent(ticker="AAPL", data_type="info")
# Info is huge, just print some keys
if "data" in res1:
    print(f"Success! Keys found: {list(res1['data'].keys())[:5]}")
else:
    print(res1)

print("\n--- 2. PENTEST AGENT SCRIPT TEST ---")
res2 = pentest_agent(target="scanme.nmap.org", scan_type="quick")
print(res2)

print("\n--- 3. CONTRACT ANALYSIS AGENT SCRIPT TEST ---")
res3 = contract_analysis_agent(file_path="dummy_contract.txt")
print(json.dumps(res3, indent=2))

print("\n--- 4. DATA SCIENCE AGENT SCRIPT TEST ---")
res4 = data_science_agent(dataset_path="dummy_dataset.csv", target_column="price", task_type="regression")
print(json.dumps(res4, indent=2))
