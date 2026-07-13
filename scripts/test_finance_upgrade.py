import json
from agents.finance_agent import finance_agent

print("--- TEST 1: MARKET TRENDING ---")
res1 = finance_agent(ticker="MARKET", data_type="trending")
if "data" in res1 and 'quotes' in res1['data']:
    print(f"Top 3 Trending: {[q['symbol'] for q in res1['data']['quotes'][:3]]}")
else:
    print(res1)

print("\n--- TEST 2: AAPL SEC FILINGS ---")
res2 = finance_agent(ticker="AAPL", data_type="sec_filings")
if "data" in res2 and isinstance(res2['data'], list) and len(res2['data']) > 0:
    print(f"Found {len(res2['data'])} filings.")
    print("Sample filing keys:", list(res2['data'][0].keys()))
else:
    print(res2)

print("\n--- TEST 3: AAPL ANALYSIS (Recommendations) ---")
res3 = finance_agent(ticker="AAPL", data_type="analysis")
if "data" in res3 and isinstance(res3['data'], list) and len(res3['data']) > 0:
    print(f"Found {len(res3['data'])} recommendation trends.")
    print("Sample keys:", list(res3['data'][0].keys()))
else:
    print(res3)
