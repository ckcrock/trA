import asyncio
import os
import sys
import logging
import threading
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Path setup
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from src.adapters.angel.auth import AngelAuthManager
from src.adapters.angel.data_client import AngelDataClient
from src.adapters.angel.websocket_client import AngelWebSocketClient
from src.adapters.angel.rate_limiter import TokenBucketRateLimiter

# Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("DataTest")

async def main():
    load_dotenv()
    
    # 1. Auth checks
    api_key = os.getenv("ANGEL_API_KEY")
    if not api_key:
        logger.error("❌ ANGEL_API_KEY not found in .env")
        return

    logger.info("Initializing Auth...")
    auth = AngelAuthManager(
        api_key=api_key,
        client_code=os.getenv("ANGEL_CLIENT_CODE"),
        mpin=os.getenv("ANGEL_PASSWORD"),
        totp_secret=os.getenv("ANGEL_TOTP_SECRET")
    )
    
    if not auth.login():
        logger.error("❌ Login failed. Check credentials in .env")
        return
    else:
        logger.info("✅ Login successful")

    # 2. Historical Data
    logger.info("\n--- Testing Historical Data ---")
    rate_limiter = TokenBucketRateLimiter(3.0)
    data_client = AngelDataClient(auth, rate_limiter)
    
    try:
        # SBIN (NSE) = 3045
        symbol = "3045"
        exchange = "NSE"
        logger.info(f"Fetching 30 days history for Token: {symbol} ({exchange})")
        
        hist_data = await data_client.get_historical_data(
            symbol_token=symbol,
            exchange=exchange,
            interval="ONE_MINUTE",
            from_date=datetime.now() - timedelta(days=1),
            to_date=datetime.now()
        )
        if hist_data is not None and not hist_data.empty:
            logger.info(f"✅ Historical Data Received: {len(hist_data)} rows")
            print(hist_data.tail())
        else:
            logger.warning("⚠️ No historical data received (Market closed? Invalid token?)")
    except Exception as e:
        logger.error(f"❌ Historical Data Error: {e}")
        import traceback
        traceback.print_exc()

    # 3. WebSocket
    logger.info("\n--- Testing WebSocket ---")
    ws_client = AngelWebSocketClient(auth)
    
    received_ticks = []
    def on_tick(tick):
        # logger.info(f"Tick received: {tick}")
        received_ticks.append(tick)
        if len(received_ticks) % 5 == 0:
            logger.info(f"Received {len(received_ticks)} ticks so far...")
        
    ws_client.register_callback(on_tick)
    
    # Run connection in thread
    ws_thread = threading.Thread(target=ws_client.connect)
    ws_thread.daemon = True
    ws_thread.start()
    
    logger.info("WebSocket thread started. Waiting for connection...")
    
    # Wait for connection
    for _ in range(10):
        if ws_client.is_connected:
            break
        await asyncio.sleep(0.5)
        
    if not ws_client.is_connected:
        logger.warning("⚠️ WebSocket not connected after 5s. Proceeding anyway (might rely on auto-reconnect).")
    
    try:
        # Subscribe to SBIN (3045) and NIFTY (99926000)
        token_list = [{"exchangeType": 1, "tokens": ["3045", "99926000"]}] 
        logger.info(f"Subscribing to: {token_list}")
        
        ws_client.subscribe(mode=1, token_list=token_list) # Mode 1 = LTP
        
        logger.info("Listening for ticks (10s)...")
        await asyncio.sleep(10)
        
        ws_client.close()
        
        if received_ticks:
            logger.info(f"✅ WebSocket Test Passed: Received {len(received_ticks)} ticks")
            logger.info(f"Sample tick: {received_ticks[0]}")
        else:
            logger.warning("⚠️ No ticks received (Market likely closed or connection failed)")
            
    except Exception as e:
        logger.error(f"❌ WebSocket Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
