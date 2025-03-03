"""
Spy v2 - Consolidated Backend Code
===================================
This file contains the enhanced trading algorithm logic, a Flask API,
and references to environment variables for secure connections to Supabase.

Features & Enhancements:
1. Modular trade signal generation via detect_trade_signal().
2. Basic risk management function manage_risk().
3. Flask endpoints:
   - /test: Quick health check endpoint.
   - /api/execute-trade: Inserts a new trade (service_role usage).
   - /api/trades: Retrieves trades from Supabase (bypassing RLS if using service_role).
4. References user_id for future expansions with RLS. 
   (If using service_role, RLS is bypassed. For user-facing reads, the anon key + RLS can restrict 
   to user_id = auth.uid().)

Dependencies (requirements.txt):
--------------------------------
flask
supabase-py
python-dotenv

Optional additions:
- requests (if you make external HTTP calls)
- more advanced libraries for AI/ML or technical analysis

Usage:
------
1. Load environment variables (SUPABASE_URL, SUPABASE_KEY) from .env or Render/Vercel secrets.
2. Run with: 
   python spy_backend.py
   (In production, set the PORT environment variable if your platform requires it.)
3. Endpoints:
   - GET  /test
   - POST /api/execute-trade
   - GET  /api/trades
"""

import os
from flask import Flask, request, jsonify
from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables from a local .env file (for development).
# In production (e.g., on Render), these come from environment variables set in the platform.
load_dotenv()

# Retrieve Supabase credentials from environment variables
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Initialize Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Create Flask app
app = Flask(__name__)

def detect_trade_signal(data: dict) -> str:
    """
    Determines a trade signal based on market indicators.

    Parameters:
        data (dict): Market data with keys like:
            - "ADX": Average Directional Index (trend strength)
            - "price": Current market price
            - "VWAP": Volume Weighted Average Price
            (You can add more, e.g., RSI, MACD, etc.)

    Returns:
        str: "Bullish Signal", "Bearish Signal", or "No Trade"

    Notes:
        - This logic is basic: If ADX > 25 and price > VWAP, we call it "Bullish Signal".
          If ADX > 25 and price < VWAP, "Bearish Signal". Otherwise, "No Trade".
        - You can expand or refine thresholds, weighting, or additional indicators.
    """
    adx = data.get("ADX", 0)
    price = data.get("price", 0)
    vwap = data.get("VWAP", 0)

    if adx > 25 and price > vwap:
        return "Bullish Signal"
    elif adx > 25 and price < vwap:
        return "Bearish Signal"
    else:
        return "No Trade"

def manage_risk(trade: dict, stop_loss: float = 0.5, take_profit: float = 1.0) -> dict:
    """
    Applies basic risk management to an open trade.

    Parameters:
        trade (dict): The trade data, expected keys:
            - "entry_price": The entry price of the trade
            - "profit": Current profit (float)
            - "loss": Current loss (float)
            - "status": "open" or "executed" typically
        stop_loss (float): Multiplier for stop-loss threshold
        take_profit (float): Multiplier for take-profit threshold

    Returns:
        dict: Updated trade dict. If thresholds are exceeded, status is set to "closed".

    Example:
        If entry_price=400, stop_loss=0.5 => trade closes if loss >= 0.5*400=200.
        If take_profit=1.0 => trade closes if profit >= 1.0*400=400.
    """
    entry_price = trade.get("entry_price", 0)
    if entry_price == 0:
        return trade  # Avoid division by zero

    loss = trade.get("loss", 0)
    profit = trade.get("profit", 0)

    if loss >= stop_loss * entry_price:
        trade["status"] = "closed"
    elif profit >= take_profit * entry_price:
        trade["status"] = "closed"

    return trade

@app.route('/test', methods=['GET'])
def test_route():
    """
    Simple health-check endpoint.
    You can visit /test to confirm the server is running.
    """
    return jsonify({"message": "Spy MVP is running!"})

@app.route('/api/execute-trade', methods=['POST'])
def execute_trade():
    """
    Inserts a new trade record into the 'trades' table using service_role privileges.
    Expects JSON data like:
    {
      "signal": "Bullish Signal",
      "broker": "IBKR",
      "capital_allocation": 1000,
      "entry_price": 400,
      "user_id": "some-uuid"  (if you plan to store user ownership)
    }

    Because we're using the service_role key, RLS is bypassed and we can do full inserts.
    """
    payload = request.get_json()
    if not payload:
        return jsonify({"status": "error", "message": "No JSON payload provided"}), 400

    signal = payload.get("signal", "No Signal")
    broker = payload.get("broker", "Unknown")
    capital_allocation = payload.get("capital_allocation", 0)
    entry_price = payload.get("entry_price", 0)
    user_id = payload.get("user_id", None)  # if storing user ownership
    status = "executed"

    # Insert into Supabase 'trades' table
    response = supabase.table("trades").insert({
        "signal": signal,
        "broker": broker,
        "capital_allocation": capital_allocation,
        "entry_price": entry_price,
        "status": status,
        "user_id": user_id  # optional, if your table has a user_id column
    }).execute()

    return jsonify({"status": "success", "data": response.data}), 201

@app.route('/api/trades', methods=['GET'])
def get_trades():
    """
    Retrieves all trades from the 'trades' table.
    If using service_role, this bypasses RLS. If you want to limit data by user,
    you can either:
    1) Switch to the anon key + RLS policy, or
    2) Filter results by user_id in code.

    For now, this returns all trades (since we are service_role).
    """
    response = supabase.table("trades").select("*").execute()
    return jsonify({"status": "success", "data": response.data}), 200

if __name__ == "__main__":
    # Use an environment variable PORT if provided, else default to 5002.
    # This is useful for hosting on Render or other platforms that auto-assign ports.
    port = int(os.getenv("PORT", 5002))
    app.run(host="0.0.0.0", port=port, debug=True)

