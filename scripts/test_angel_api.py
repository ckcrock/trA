"""
Angel One API Test Script
Tests: Login, LTP, Historical Data (with retry), WebSocket (live ticks)

Usage:
    venv\\Scripts\\python.exe scripts\\test_angel_api.py
"""
import asyncio
import os
import sys
import io
import time
import logging
import threading
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Fix Windows console encoding for emoji/unicode
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s: %(message)s'
)
logger = logging.getLogger("AngelTest")

# Suppress noisy SDK logs
logging.getLogger("SmartApi.smartConnect").setLevel(logging.WARNING)


async def test_login(auth):
    """Test 1: Login"""
    print("\n" + "=" * 60)
    print("TEST 1: LOGIN")
    print("=" * 60)
    
    success = auth.login()
    if success:
        print(f"  ✅ Login successful as {auth.client_code}")
        print(f"  📋 Feed token: {auth.feed_token[:20]}..." if auth.feed_token else "  ⚠️ No feed token")
        print(f"  📋 Access token: {auth.access_token[:20]}..." if auth.access_token else "  ⚠️ No access token")
        print(f"  ⏰ Session expires: {auth.session_expiry}")
    else:
        print("  ❌ Login FAILED")
    return success


async def test_ltp(auth):
    """Test 2: LTP fetch"""
    print("\n" + "=" * 60)
    print("TEST 2: LTP (Last Traded Price)")
    print("=" * 60)
    
    try:
        client = auth.get_smart_api_client()
        response = client.ltpData("NSE", "SBIN-EQ", "3045")
        
        if response and response.get('status'):
            data = response.get('data', {})
            ltp = data.get('ltp', 'N/A')
            print(f"  ✅ SBIN LTP: ₹{ltp}")
            print(f"  📋 Full response: {data}")
            return True
        else:
            error_msg = response.get('message', 'Unknown') if response else 'No response'
            print(f"  ❌ LTP fetch failed: {error_msg}")
            return False
    except Exception as e:
        print(f"  ❌ LTP exception: {e}")
        return False


async def test_historical(auth):
    """Test 3: Historical data with retry"""
    print("\n" + "=" * 60)
    print("TEST 3: HISTORICAL DATA (with retry)")
    print("=" * 60)
    
    from src.adapters.angel.rate_limiter import TokenBucketRateLimiter
    from src.adapters.angel.data_client import AngelDataClient
    
    rate_limiter = TokenBucketRateLimiter(rate=3, capacity=3)
    data_client = AngelDataClient(auth_manager=auth, rate_limiter=rate_limiter)
    
    to_date = datetime.now()
    from_date = to_date - timedelta(days=5)
    
    print(f"  📅 Requesting: {from_date.strftime('%Y-%m-%d')} → {to_date.strftime('%Y-%m-%d')}")
    print(f"  🔧 Interval: ONE_DAY, Symbol: SBIN (3045)")
    
    df = await data_client.get_historical_data(
        symbol_token="3045",
        exchange="NSE",
        interval="ONE_DAY",
        from_date=from_date,
        to_date=to_date
    )
    
    if df is not None and not df.empty:
        print(f"  ✅ Got {len(df)} candles!")
        print(f"\n{df.to_string(index=False)}\n")
        return True
    else:
        print("  ❌ Historical data returned None/empty (after retries)")
        return False


def test_websocket(auth, duration=15):
    """Test 4: WebSocket live ticks"""
    print("\n" + "=" * 60)
    print(f"TEST 4: WEBSOCKET (listening for {duration}s)")
    print("=" * 60)
    
    from SmartApi.smartWebSocketV2 import SmartWebSocketV2
    
    tick_count = 0
    ws_connected = threading.Event()
    ws_done = threading.Event()
    
    try:
        sws = SmartWebSocketV2(
            auth_token=auth.access_token,
            api_key=auth.api_key,
            client_code=auth.client_code,
            feed_token=auth.feed_token,
            max_retry_attempt=2
        )
    except Exception as e:
        print(f"  ❌ WebSocket init failed: {e}")
        return False
    
    def on_data(wsapp, message):
        nonlocal tick_count
        tick_count += 1
        token = message.get('token', '?')
        ltp = message.get('last_traded_price', 0) / 100  # SDK returns price * 100
        mode = message.get('subscription_mode_val', '?')
        print(f"  📊 Tick #{tick_count}: token={token} LTP=₹{ltp:.2f} mode={mode}")
        
        if tick_count >= 5:
            print(f"  ✅ Received {tick_count} ticks! Closing...")
            ws_done.set()
    
    def on_open(wsapp):
        print("  ✅ WebSocket connected!")
        ws_connected.set()
        # Subscribe to SBIN (token 3045) on NSE_CM (exchangeType=1)
        # Mode 2 = QUOTE (LTP + volume + bid/ask)
        token_list = [{"exchangeType": 1, "tokens": ["3045"]}]
        sws.subscribe("sbin_test1", 2, token_list)
        print("  📡 Subscribed to SBIN (3045) in QUOTE mode")
    
    def on_error(wsapp, error=None):
        print(f"  ❌ WebSocket error: {error}")
        ws_done.set()
    
    def on_close(wsapp, *args):
        print("  ℹ️ WebSocket closed")
        ws_done.set()
    
    sws.on_open = on_open
    sws.on_data = on_data
    sws.on_error = on_error
    sws.on_close = on_close
    
    # Run WebSocket in a separate thread (it blocks)
    ws_thread = threading.Thread(target=sws.connect, daemon=True)
    ws_thread.start()
    
    # Wait for connection or timeout
    if not ws_connected.wait(timeout=10):
        print("  ❌ WebSocket connection timeout (10s)")
        try:
            sws.close_connection()
        except:
            pass
        return False
    
    # Wait for ticks or duration timeout
    ws_done.wait(timeout=duration)
    
    try:
        sws.close_connection()
    except:
        pass
    
    if tick_count > 0:
        print(f"  ✅ WebSocket test PASSED ({tick_count} ticks received)")
        return True
    else:
        print("  ⚠️ WebSocket connected but no ticks received (market may be closed)")
        return True  # Connected successfully, just no data


async def main():
    load_dotenv()
    
    api_key = os.getenv("ANGEL_API_KEY")
    client_code = os.getenv("ANGEL_CLIENT_CODE")
    mpin = os.getenv("ANGEL_PASSWORD")
    totp_secret = os.getenv("ANGEL_TOTP_SECRET")
    
    if not all([api_key, client_code, mpin, totp_secret]):
        print("❌ Missing credentials. Set these in .env:")
        print("   ANGEL_API_KEY, ANGEL_CLIENT_CODE, ANGEL_PASSWORD, ANGEL_TOTP_SECRET")
        return
    
    from src.adapters.angel.auth import AngelAuthManager
    auth = AngelAuthManager(
        api_key=api_key,
        client_code=client_code,
        mpin=mpin,
        totp_secret=totp_secret
    )
    
    results = {}
    
    # Test 1: Login
    results['login'] = await test_login(auth)
    if not results['login']:
        print("\n❌ Login failed — skipping remaining tests")
        return
    
    # Test 2: LTP
    results['ltp'] = await test_ltp(auth)
    
    # Test 3: Historical data
    results['historical'] = await test_historical(auth)
    
    # Test 4: WebSocket
    results['websocket'] = test_websocket(auth, duration=15)
    
    # Summary
    print("\n" + "=" * 60)
    print("RESULTS SUMMARY")
    print("=" * 60)
    for test, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {test:20s} {status}")
    
    total = sum(results.values())
    print(f"\n  {total}/{len(results)} tests passed")
    
    # Cleanup
    try:
        auth.logout()
    except:
        pass


if __name__ == "__main__":
    asyncio.run(main())
