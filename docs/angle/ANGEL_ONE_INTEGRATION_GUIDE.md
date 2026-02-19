# ANGEL ONE SMARTAPI - COMPLETE INTEGRATION GUIDE
## Production-Ready Python Implementation

**Complete API integration with authentication, market data, orders, WebSocket streaming, and portfolio management.**

---

## 📦 TABLE OF CONTENTS

1. [Features](#features)
2. [Prerequisites](#prerequisites)
3. [Installation](#installation)
4. [Quick Start](#quick-start)
5. [Authentication](#authentication)
6. [Market Data](#market-data)
7. [Order Management](#order-management)
8. [Portfolio Management](#portfolio-management)
9. [WebSocket Streaming](#websocket-streaming)
10. [GTT Orders](#gtt-orders)
11. [Error Handling](#error-handling)
12. [Rate Limits](#rate-limits)
13. [Best Practices](#best-practices)
14. [Troubleshooting](#troubleshooting)

---

## ✨ FEATURES

### ✅ Authentication & Session Management
- MPIN + TOTP based login (latest Angel One requirement)
- Automatic session refresh (every 5 hours)
- Session expiry handling
- Token management

### ✅ Market Data
- Real-time LTP (Last Traded Price)
- Full market quotes (bid/ask, volume, depth)
- Historical OHLCV data
- Multiple timeframes (1-min to daily)
- Intraday data fetching

### ✅ Order Management
- Place orders (Market, Limit, Stop-Loss, SL-M)
- Modify orders
- Cancel orders
- Order status tracking
- Order book & trade book
- All product types (Delivery, Intraday, F&O)

### ✅ Portfolio Management
- Holdings (delivery positions)
- Positions (intraday + overnight)
- Position conversion (MIS to CNC)
- P&L tracking
- RMS limits (available margin)

### ✅ WebSocket Streaming
- Live tick data (real-time)
- Multiple subscription modes (LTP, QUOTE, SNAP_QUOTE)
- Automatic reconnection
- Multi-symbol support
- Thread-safe operation

### ✅ GTT Orders
- Long-term trigger orders
- Create, modify, cancel GTT
- GTT order listing

### ✅ Production Features
- Comprehensive error handling
- Logging with log levels
- Rate limit awareness
- Automatic retries
- Connection pooling

---

## 📋 PREREQUISITES

### 1. Angel One Account
- Active Angel One trading account
- SmartAPI subscription (free)

### 2. API Credentials
You need the following:

**a) API Key & Secret**
1. Go to https://smartapi.angelbroking.com/
2. Sign up / Login
3. Create a new app (Trading APIs)
4. Note down your API Key

**b) Client Code**
- Your Angel One client code (e.g., "A123456")

**c) MPIN**
- Your Angel One MPIN (4-digit)
- **NOT your password** (Angel One changed login to MPIN-based in Jan 2025)

**d) TOTP Secret**
1. Enable 2FA in Angel One app
2. When setting up authenticator, choose "Enter key manually"
3. Copy the secret key (32-character string)
4. This is your TOTP secret

### 3. Python Environment
- Python 3.8 or higher
- pip package manager

---

## 🚀 INSTALLATION

### Step 1: Install Dependencies

```bash
# Install Angel One SDK
pip install smartapi-python

# Install other required packages
pip install pyotp pandas requests
```

### Step 2: Download Integration File

Save `angel_one_complete_integration.py` to your project directory.

### Step 3: Set Environment Variables (Recommended)

**Linux/Mac:**
```bash
export ANGEL_API_KEY="your_api_key"
export ANGEL_CLIENT_CODE="your_client_code"
export ANGEL_MPIN="your_mpin"
export ANGEL_TOTP_SECRET="your_totp_secret"
```

**Windows:**
```cmd
set ANGEL_API_KEY=your_api_key
set ANGEL_CLIENT_CODE=your_client_code
set ANGEL_MPIN=your_mpin
set ANGEL_TOTP_SECRET=your_totp_secret
```

**Or create a `.env` file:**
```
ANGEL_API_KEY=your_api_key
ANGEL_CLIENT_CODE=your_client_code
ANGEL_MPIN=your_mpin
ANGEL_TOTP_SECRET=your_totp_secret
```

---

## ⚡ QUICK START

### Basic Usage

```python
from angel_one_complete_integration import AngelOneClient

# Initialize client (auto-login enabled)
client = AngelOneClient(
    api_key="your_api_key",
    client_code="your_client_code",
    mpin="your_mpin",
    totp_secret="your_totp_secret"
)

# Get LTP
ltp = client.market_data.get_ltp("NSE", "3045", "SBIN-EQ")
print(f"SBIN LTP: ₹{ltp}")

# Place market order
order_id = client.orders.place_order(
    trading_symbol="SBIN-EQ",
    symbol_token="3045",
    exchange="NSE",
    transaction_type="BUY",
    quantity=1,
    order_type="MARKET",
    product_type="INTRADAY"
)

# Get positions
positions = client.portfolio.get_positions()
print(f"Open positions: {len(positions['net'])}")

# Logout
client.logout()
```

---

## 🔐 AUTHENTICATION

### Manual Login

```python
from angel_one_complete_integration import AngelOneAuth

# Initialize auth (no auto-login)
auth = AngelOneAuth(
    api_key="your_api_key",
    client_code="your_client_code",
    mpin="your_mpin",
    totp_secret="your_totp_secret"
)

# Login
success = auth.login()
if success:
    print("✅ Login successful!")
    print(f"JWT Token: {auth.jwt_token}")
    print(f"Session expires: {auth.session_expiry}")
else:
    print("❌ Login failed")
```

### Session Management

```python
# Check if session is valid
if auth.is_session_valid():
    print("✅ Session is valid")
else:
    print("⚠️ Session expired or expiring soon")

# Refresh session
auth.refresh_session()

# Ensure authenticated (auto-refresh if needed)
auth.ensure_authenticated()

# Logout
auth.logout()
```

### Auto-Refresh

The session automatically refreshes every 5 hours. To disable:

```python
auth.auto_refresh_enabled = False
```

---

## 📊 MARKET DATA

### Get Last Traded Price (LTP)

```python
from angel_one_complete_integration import AngelOneClient

client = AngelOneClient(...)

# Get LTP for SBIN
ltp = client.market_data.get_ltp(
    exchange="NSE",
    symbol_token="3045",
    trading_symbol="SBIN-EQ"
)
print(f"SBIN LTP: ₹{ltp}")

# Get LTP for Nifty 50
nifty_ltp = client.market_data.get_ltp(
    exchange="NSE",
    symbol_token="26000",
    trading_symbol="NIFTY50"
)
print(f"Nifty 50: {nifty_ltp}")
```

### Get Full Quote

```python
# Get full quote with bid/ask and depth
quote = client.market_data.get_quote(
    exchange="NSE",
    symbol_token="3045",
    trading_symbol="SBIN-EQ"
)

if quote:
    print(f"LTP: {quote['ltp']}")
    print(f"Open: {quote['open']}")
    print(f"High: {quote['high']}")
    print(f"Low: {quote['low']}")
    print(f"Close: {quote['close']}")
    print(f"Volume: {quote['volume']}")
```

### Historical Data

```python
from datetime import datetime, timedelta

# Get last 30 days of 5-minute data
from_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d 09:15")
to_date = datetime.now().strftime("%Y-%m-%d 15:30")

df = client.market_data.get_historical_data(
    exchange="NSE",
    symbol_token="3045",
    interval="FIVE_MINUTE",  # ONE_MINUTE, THREE_MINUTE, FIVE_MINUTE, etc.
    from_date=from_date,
    to_date=to_date
)

print(df.head())
```

**Available Intervals:**
- ONE_MINUTE
- THREE_MINUTE
- FIVE_MINUTE
- TEN_MINUTE
- FIFTEEN_MINUTE
- THIRTY_MINUTE
- ONE_HOUR
- ONE_DAY

### Get Today's Intraday Data

```python
# Convenience method for today's data
df = client.market_data.get_intraday_data(
    symbol_token="3045",
    exchange="NSE",
    interval="FIVE_MINUTE"
)
```

---

## 📝 ORDER MANAGEMENT

### Place Market Order

```python
# Buy 1 share of SBIN (Intraday)
order_id = client.orders.place_order(
    trading_symbol="SBIN-EQ",
    symbol_token="3045",
    exchange="NSE",
    transaction_type="BUY",  # or "SELL"
    quantity=1,
    order_type="MARKET",
    product_type="INTRADAY"  # or "DELIVERY", "CARRYFORWARD"
)

if order_id:
    print(f"✅ Order placed! Order ID: {order_id}")
```

### Place Limit Order

```python
# Buy at specific price
order_id = client.orders.place_order(
    trading_symbol="SBIN-EQ",
    symbol_token="3045",
    exchange="NSE",
    transaction_type="BUY",
    quantity=1,
    order_type="LIMIT",
    product_type="INTRADAY",
    price=720.50  # Limit price
)
```

### Place Stop-Loss Order

```python
# Stop-Loss Limit order
order_id = client.orders.place_order(
    trading_symbol="SBIN-EQ",
    symbol_token="3045",
    exchange="NSE",
    transaction_type="SELL",
    quantity=1,
    order_type="STOPLOSS_LIMIT",
    product_type="INTRADAY",
    price=710.00,        # Limit price
    trigger_price=712.00  # Stop-loss trigger
)

# Stop-Loss Market order
order_id = client.orders.place_order(
    trading_symbol="SBIN-EQ",
    symbol_token="3045",
    exchange="NSE",
    transaction_type="SELL",
    quantity=1,
    order_type="STOPLOSS_MARKET",
    product_type="INTRADAY",
    trigger_price=712.00  # Trigger price only
)
```

### Modify Order

```python
# Modify quantity and price
success = client.orders.modify_order(
    order_id="241216000123456",
    variety="NORMAL",
    quantity=2,           # New quantity
    price=721.00,         # New price
    order_type="LIMIT"
)
```

### Cancel Order

```python
# Cancel order
success = client.orders.cancel_order(
    order_id="241216000123456",
    variety="NORMAL"
)
```

### Get Order Book

```python
# Get all orders for the day
orders = client.orders.get_order_book()

for order in orders:
    print(f"Order ID: {order['orderid']}")
    print(f"Symbol: {order['tradingsymbol']}")
    print(f"Status: {order['orderstatus']}")
    print(f"Quantity: {order['quantity']}")
    print("-" * 40)
```

### Get Order Status

```python
# Get specific order status
order = client.orders.get_order_status("241216000123456")

if order:
    print(f"Status: {order['orderstatus']}")
    print(f"Filled: {order['filledshares']}")
    print(f"Price: {order['averageprice']}")
```

### Get Trade Book

```python
# Get all executed trades
trades = client.orders.get_trade_book()

for trade in trades:
    print(f"Trade ID: {trade['tradeid']}")
    print(f"Symbol: {trade['tradingsymbol']}")
    print(f"Quantity: {trade['quantity']}")
    print(f"Price: {trade['tradeprice']}")
```

---

## 💼 PORTFOLIO MANAGEMENT

### Get Holdings

```python
# Get all delivery holdings
holdings = client.portfolio.get_holdings()

for holding in holdings:
    print(f"Symbol: {holding['tradingsymbol']}")
    print(f"Quantity: {holding['quantity']}")
    print(f"Avg Price: {holding['averageprice']}")
    print(f"LTP: {holding['ltp']}")
    print(f"P&L: {holding['pnl']}")
    print("-" * 40)
```

### Get Positions

```python
# Get open positions
positions = client.portfolio.get_positions()

# Net positions (overall)
for pos in positions['net']:
    print(f"Symbol: {pos['tradingsymbol']}")
    print(f"Quantity: {pos['netqty']}")
    print(f"Avg Price: {pos['netprice']}")
    print(f"P&L: {pos['pnl']}")

# Day positions (today's trades)
for pos in positions['day']:
    print(f"Symbol: {pos['tradingsymbol']}")
    print(f"Quantity: {pos['buyqty']} - {pos['sellqty']}")
```

### Convert Position

```python
# Convert MIS (intraday) to CNC (delivery)
success = client.portfolio.convert_position(
    exchange="NSE",
    trading_symbol="SBIN-EQ",
    transaction_type="BUY",
    position_type="DAY",
    quantity=1,
    old_product_type="INTRADAY",
    new_product_type="DELIVERY"
)
```

### Get Available Margin

```python
# Get RMS limits
limits = client.portfolio.get_rms_limits()

if limits:
    print(f"Available Cash: ₹{limits['availablecash']}")
    print(f"Available Margin: ₹{limits['availablemargin']}")
    print(f"Used Margin: ₹{limits['usedmargin']}")
```

---

## 📡 WEBSOCKET STREAMING

### Basic WebSocket Usage

```python
from angel_one_complete_integration import AngelOneClient, AngelWebSocket

client = AngelOneClient(...)

# Define callback for tick data
def on_tick(tick_data):
    print(f"📊 Tick: {tick_data}")

# Define callback for connection
def on_connect():
    print("✅ WebSocket connected!")
    # Subscribe to SBIN
    client.websocket.subscribe("3045", "nse_cm", AngelWebSocket.MODE_QUOTE)

# Start WebSocket
client.start_websocket(
    on_tick=on_tick,
    on_connect=on_connect
)

# Keep running
import time
time.sleep(3600)  # Run for 1 hour

# Stop WebSocket
client.stop_websocket()
```

### Subscribe to Multiple Symbols

```python
def on_connect():
    print("✅ Connected! Subscribing to multiple symbols...")
    
    # Subscribe to multiple stocks
    symbols = [
        ("3045", "nse_cm"),   # SBIN
        ("1333", "nse_cm"),   # HDFC Bank
        ("2885", "nse_cm"),   # Reliance
    ]
    
    for token, exchange in symbols:
        client.websocket.subscribe(token, exchange, AngelWebSocket.MODE_QUOTE)
```

### Subscription Modes

```python
# MODE_LTP = 1 (Only last traded price)
client.websocket.subscribe("3045", "nse_cm", 1)

# MODE_QUOTE = 2 (LTP + Bid/Ask + Volume)
client.websocket.subscribe("3045", "nse_cm", 2)

# MODE_SNAP_QUOTE = 3 (Full market depth)
client.websocket.subscribe("3045", "nse_cm", 3)
```

### Exchange Segments

```python
# NSE Cash
"nse_cm"

# NSE F&O
"nse_fo"

# BSE Cash
"bse_cm"

# MCX
"mcx_fo"
```

### Unsubscribe

```python
# Unsubscribe from symbol
client.websocket.unsubscribe("3045")
```

---

## 📌 GTT ORDERS

### Create GTT Order

```python
# Create GTT: Buy 1 SBIN when price reaches 750
gtt_id = client.gtt.create_gtt(
    trading_symbol="SBIN-EQ",
    symbol_token="3045",
    exchange="NSE",
    transaction_type="BUY",
    quantity=1,
    price=750.00,           # Execution price
    trigger_price=750.00,   # Trigger price
    product_type="DELIVERY"
)

if gtt_id:
    print(f"✅ GTT created! GTT ID: {gtt_id}")
```

### Get GTT List

```python
# Get all active GTT orders
gtt_list = client.gtt.get_gtt_list()

for gtt in gtt_list:
    print(f"GTT ID: {gtt['id']}")
    print(f"Symbol: {gtt['tradingsymbol']}")
    print(f"Trigger: {gtt['triggerprice']}")
    print(f"Status: {gtt['status']}")
```

### Cancel GTT Order

```python
# Cancel GTT
success = client.gtt.cancel_gtt(gtt_id=12345)
```

---

## ⚠️ ERROR HANDLING

### Try-Except Blocks

```python
try:
    order_id = client.orders.place_order(...)
    if order_id:
        print(f"Order placed: {order_id}")
    else:
        print("Order placement failed - check logs")
except Exception as e:
    print(f"Exception: {e}")
```

### Common Error Codes

| Code | Meaning | Solution |
|------|---------|----------|
| AB2005 | Insufficient margin | Check available margin |
| AB1004 | Position limit exceeded | Close some positions |
| AB1012 | Price outside circuit | Check circuit limits |
| AG8001 | Invalid session | Re-login |
| AG8002 | Session expired | Refresh or re-login |

### Logging

```python
import logging

# Set log level
logging.basicConfig(level=logging.DEBUG)

# This will show detailed logs for debugging
```

---

## 🚦 RATE LIMITS

Angel One API has rate limits:

| Endpoint | Limit |
|----------|-------|
| Historical Data | 3 requests/second |
| Order Placement | 10 requests/second |
| LTP/Quote | 5 requests/second |
| WebSocket | No documented limit (reasonable use) |

**Best Practices:**
- Cache historical data
- Don't poll LTP in loops (use WebSocket)
- Batch order placements if possible
- Implement exponential backoff on errors

---

## ✅ BEST PRACTICES

### 1. Use Environment Variables

```python
import os

API_KEY = os.getenv("ANGEL_API_KEY")
CLIENT_CODE = os.getenv("ANGEL_CLIENT_CODE")
MPIN = os.getenv("ANGEL_MPIN")
TOTP_SECRET = os.getenv("ANGEL_TOTP_SECRET")

client = AngelOneClient(API_KEY, CLIENT_CODE, MPIN, TOTP_SECRET)
```

### 2. Automatic Session Management

```python
# Always use ensure_authenticated before API calls
client.auth.ensure_authenticated()

# Or use the client methods which do this automatically
client.orders.place_order(...)  # Auto-ensures auth
```

### 3. Error Handling

```python
# Always wrap API calls in try-except
try:
    ltp = client.market_data.get_ltp(...)
    if ltp:
        # Process LTP
        pass
except Exception as e:
    logger.error(f"Error: {e}")
```

### 4. WebSocket Reconnection

The WebSocket automatically reconnects on disconnection. But add your own error handling:

```python
def on_error(error):
    logger.error(f"WebSocket error: {error}")
    # Add custom error handling here
```

### 5. Daily Logout

```python
# Logout at end of trading day
import schedule

def logout_task():
    client.logout()

schedule.every().day.at("15:40").do(logout_task)
```

---

## 🐛 TROUBLESHOOTING

### Issue: Login Failed

**Possible Causes:**
1. Wrong MPIN (not password!)
2. TOTP secret incorrect
3. 2FA not enabled on Angel One app

**Solution:**
- Verify MPIN (4-digit)
- Re-generate TOTP secret from Angel One app
- Enable 2FA in Angel One mobile app

### Issue: Session Expired

**Solution:**
```python
# Refresh session
client.auth.refresh_session()

# Or re-login
client.auth.login()
```

### Issue: Order Rejected (AB2005)

**Cause:** Insufficient margin

**Solution:**
```python
# Check available margin
limits = client.portfolio.get_rms_limits()
print(f"Available: {limits['availablecash']}")
```

### Issue: WebSocket Not Connecting

**Solution:**
1. Check if logged in: `client.auth.is_session_valid()`
2. Check internet connection
3. Check firewall settings
4. Restart WebSocket: `client.stop_websocket()` then `client.start_websocket(...)`

### Issue: Historical Data Not Downloading

**Causes:**
1. Rate limit exceeded (3 req/sec)
2. Invalid date range
3. Invalid symbol token

**Solution:**
```python
# Add delay between requests
import time
time.sleep(0.4)  # 400ms delay = 2.5 req/sec

# Verify date format
from_date = "2024-01-01 09:15"  # YYYY-MM-DD HH:MM
```

---

## 📚 ADDITIONAL RESOURCES

**Official Documentation:**
- Angel One SmartAPI Docs: https://smartapi.angelbroking.com/docs/
- Python SDK GitHub: https://github.com/angel-one/smartapi-python
- SmartAPI Forum: https://smartapi.angelone.in/forum

**Support:**
- Email: smartapihelpdesk@angelbroking.com
- Forum: https://smartapi.angelone.in/forum

---

## 📄 LICENSE

This integration is provided as-is for educational and development purposes. 

**Disclaimer:** Trading in securities market is subject to market risks. Please read all the related documents carefully before investing.

---

## ✨ FEATURES CHECKLIST

- [x] MPIN + TOTP Authentication
- [x] Automatic session refresh
- [x] Real-time LTP & quotes
- [x] Historical data (all timeframes)
- [x] Order placement (all types)
- [x] Order modification
- [x] Order cancellation
- [x] Order book & trade book
- [x] Holdings & positions
- [x] Position conversion
- [x] RMS limits
- [x] WebSocket streaming
- [x] Multiple subscription modes
- [x] GTT orders
- [x] Comprehensive error handling
- [x] Automatic reconnection
- [x] Production-ready logging
- [x] Rate limit awareness

---

**Happy Trading! 🚀📈**
