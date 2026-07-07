"""
Agent: finance_agent
--------------------
Uses yahooquery and yfinance to fetch comprehensive stock market data, SEC filings, 
historical prices, options, and general market news.
"""

import traceback
import json

DESCRIPTION = (
    "The Ultimate Finance Analyst Agent. Use this to fetch live market data, general trending news, "
    "SEC filings, options chains, analyst recommendations, historical prices, and financial statements.\n"
    "To get general market trending news, pass ticker='MARKET' and data_type='trending'."
)

PARAMETERS = {
    "ticker": {
        "type": "string",
        "description": "The stock ticker symbol (e.g., 'AAPL'). Pass 'MARKET' to get general market trending news.",
        "required": True
    },
    "data_type": {
        "type": "string",
        "description": "The type of data to fetch. Allowed values: 'profile', 'sec_filings', 'earnings', 'analysis', 'holders', 'options', 'statistics', 'news', 'financials', 'history', 'trending'.",
        "required": True
    },
    "period": {
        "type": "string",
        "description": "Only used if data_type is 'history'. Defines the time period (e.g., '1mo', '1y', 'max'). Default is '1mo'.",
        "required": False
    }
}

def clean_dataframe(df):
    """Converts a pandas DataFrame to a clean dictionary, handling indices."""
    if df is None:
        return []
    # If the object returned is a string (e.g. error message from yahooquery), return it directly or wrapped.
    if isinstance(df, str):
        if "No " in df or "not found" in df.lower():
            return []
        return [{"message": df}]
    if not hasattr(df, 'empty') or df.empty:
        return []
        
    try:
        # If the index has a name (like symbol or date), reset it so it becomes a column
        df = df.reset_index()
        # Convert all column names to string to prevent JSON serialization errors
        df.columns = df.columns.astype(str)
        # Convert timestamps/dates to strings
        for col in df.columns:
            if df[col].dtype == 'datetime64[ns]' or df[col].dtype.name.startswith('datetime64'):
                df[col] = df[col].astype(str)
        return df.to_dict(orient='records')
    except Exception as e:
        print(f"[FinanceAgent] Dataframe cleanup error: {e}")
        return []

def finance_agent(ticker: str, data_type: str, period: str = "1mo") -> dict:
    """Fetches comprehensive financial data using yahooquery and yfinance."""
    try:
        import yfinance as yf
        from yahooquery import Ticker, get_trending
    except ImportError:
        return {"error": "setup required", "message": "Missing dependencies. Please run: pip install yfinance yahooquery pandas"}

    try:
        # General Market Handling
        if ticker.upper() == "MARKET":
            if data_type == "trending":
                trending = get_trending()
                return {"success": True, "ticker": "MARKET", "data_type": "trending", "data": trending}
            else:
                return {"error": "When ticker is 'MARKET', data_type must be 'trending'."}

        # Ticker Specific Handling
        yq_ticker = Ticker(ticker)
        yf_ticker = yf.Ticker(ticker)

        result_data = None

        if data_type == "profile":
            result_data = yq_ticker.summary_profile
        
        elif data_type == "sec_filings":
            # Returns a DataFrame of all SEC filings
            df = yq_ticker.sec_filings
            result_data = clean_dataframe(df)
            
        elif data_type == "earnings":
            result_data = yq_ticker.earnings
            
        elif data_type == "analysis":
            # Analyst recommendations, upgrades/downgrades
            df = yq_ticker.recommendation_trend
            result_data = clean_dataframe(df)
            
        elif data_type == "holders":
            df = yq_ticker.fund_ownership
            result_data = clean_dataframe(df)
            
        elif data_type == "options":
            try:
                # yfinance provides a clean list of expiration dates
                result_data = {"expiration_dates": list(yf_ticker.options)}
            except Exception as e:
                result_data = {"error": f"Could not fetch options: {e}"}
            
        elif data_type == "statistics":
            result_data = yq_ticker.key_stats
            
        elif data_type == "news":
            try:
                result_data = yf_ticker.news
            except Exception as e:
                result_data = {"error": f"Could not fetch news: {e}"}
            
        elif data_type == "financials":
            df = yq_ticker.income_statement()
            result_data = clean_dataframe(df)
            
        elif data_type == "history":
            try:
                df = yf_ticker.history(period=period)
                result_data = clean_dataframe(df)
            except Exception as e:
                result_data = {"error": f"Could not fetch history: {e}"}
            
        else:
            return {"error": f"Invalid data_type: {data_type}."}

        # Yahooquery returns dicts with the ticker as the root key for some endpoints
        # e.g., {'AAPL': {...}}
        if isinstance(result_data, dict) and ticker in result_data:
            result_data = result_data[ticker]
            if isinstance(result_data, str) and result_data.startswith("No data"):
                return {"error": f"No data found for ticker {ticker} and data_type {data_type}"}

        # Catch-all for empty data
        if not result_data:
            return {"success": True, "ticker": ticker, "data_type": data_type, "message": f"No {data_type} data available for {ticker}."}

        return {
            "success": True,
            "ticker": ticker,
            "data_type": data_type,
            "data": result_data
        }

    except Exception as e:
        return {"error": f"Failed to fetch data for {ticker}: {str(e)}", "traceback": traceback.format_exc()}
