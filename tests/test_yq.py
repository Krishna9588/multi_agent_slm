from yahooquery import Ticker, get_trending

def test_yahooquery_ticker():
    """Verify yahooquery can instantiate and query tickers."""
    aapl = Ticker("AAPL")
    assert aapl is not None

if __name__ == "__main__":
    print("--- TRENDING ---")
    trending = get_trending()
    print(trending.get('quotes', [])[:2] if 'quotes' in trending else trending)
    aapl = Ticker("AAPL")
    print("AAPL Profile:", aapl.summary_profile)
