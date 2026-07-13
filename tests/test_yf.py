import yfinance as yf

aapl = yf.Ticker("AAPL")
print("Options:", aapl.options)
print("Holders (major):", type(aapl.major_holders))
print("Holders (institutional):", type(aapl.institutional_holders))
print("Insider transactions:", type(aapl.insider_transactions))
print("Recommendations:", type(aapl.recommendations))
print("Earnings dates:", type(aapl.earnings_dates))
