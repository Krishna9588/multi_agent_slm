import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from agents.finance_agent import finance_agent

def test_finance_agent_market():
    """Verify finance agent returns trending data for MARKET."""
    res = finance_agent(ticker="MARKET", data_type="trending")
    assert "error" not in res
    assert res.get("ticker") == "MARKET"

def test_finance_agent_profile():
    """Verify finance agent retrieves profile data."""
    res = finance_agent(ticker="AAPL", data_type="profile")
    assert isinstance(res, (dict, list))

if __name__ == "__main__":
    print("Testing finance_agent...")
    print(finance_agent("AAPL", "profile"))
