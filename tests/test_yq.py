from yahooquery import Ticker, get_trending

# Test General Market Trending
print("--- TRENDING ---")
trending = get_trending()
print(trending.get('quotes', [])[:2] if 'quotes' in trending else trending)

# Test Ticker specific Data
aapl = Ticker("AAPL")
print("\n--- SUMMARY PROFILE ---")
print(type(aapl.summary_profile))
print("\n--- SEC FILINGS ---")
print(type(aapl.sec_filings))
print("\n--- EARNINGS ---")
print(type(aapl.earnings))
print("\n--- FUNDAMENTALS (Financials) ---")
print(type(aapl.income_statement()))
