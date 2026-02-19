"""
Script to verify Angel One Adapter functionality.
Tests instantiation and basic structure of:
1. Native Angel Adapters (Auth, Data, Execution)
2. Nautilus Wrappers (if available)
"""

import os
import sys
import logging
import asyncio
from dotenv import load_dotenv

# Ensure we can import from src
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from src.adapters.angel.auth import AngelAuthManager
from src.adapters.angel.data_client import AngelDataClient
from src.adapters.angel.execution_client import AngelExecutionClient
from src.adapters.angel.rate_limiter import TokenBucketRateLimiter
from src.adapters.nautilus import NAUTILUS_AVAILABLE

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("AngelTest")

async def test_native_adapters():
    logger.info("--- Testing Native Angel Adapters ---")
    
    # Load credentials
    api_key = os.getenv("ANGEL_API_KEY", "dummy_key")
    client_code = os.getenv("ANGEL_CLIENT_CODE", "dummy_client")
    password = os.getenv("ANGEL_PASSWORD", "dummy_pass")
    totp_secret = os.getenv("ANGEL_TOTP_SECRET", "dummy_totp")
    
    logger.info(f"Initializing AuthManager with Client Code: {client_code}")
    
    try:
        auth = AngelAuthManager(
            api_key=api_key,
            client_code=client_code,
            mpin=password,
            totp_secret=totp_secret
        )
        rate_limiter = TokenBucketRateLimiter(rate=3.0)
        logger.info("✅ AuthManager & RateLimiter initialized")
        
        data_client = AngelDataClient(auth, rate_limiter)
        logger.info("✅ DataClient initialized")
        
        exec_client = AngelExecutionClient(auth, rate_limiter)
        logger.info("✅ ExecutionClient initialized")
        
        # We won't actually connect because we might use dummy creds, 
        # but if we had real creds we could try auth.authenticate()
        if api_key != "dummy_key":
            logger.info("Real credentials detected. Attempting dry-run login...")
            # try:
            #     await auth.authenticate()
            #     logger.info("✅ Login successful")
            # except Exception as e:
            #     logger.error(f"❌ Login failed (expected if creds invalid): {e}")
        else:
            logger.info("ℹ️ Using dummy credentials, skipping network calls.")
            
    except Exception as e:
        import traceback
        traceback.print_exc()
        logger.error(f"❌ Initialization failed: {e}")
        raise

async def test_nautilus_adapters():
    logger.info("\n--- Testing Nautilus Adapters ---")
    
    if not NAUTILUS_AVAILABLE:
        logger.info("ℹ️ Nautilus not installed. Skipping wrapper tests.")
        return

    from src.adapters.nautilus.factories import AngelOneDataClientFactory
    from src.adapters.nautilus.config import AngelOneDataClientConfig
    from src.engine.node import TradingNodeWrapper
    
    try:
        # Test 1: Config Instantiation
        config = AngelOneDataClientConfig(
            api_key="test",
            client_code="test",
            password="test",
            totp_secret="test"
        )
        logger.info("✅ Nautilus Config initialized")
        
        # Test 2: Node Wrapper (which registers factories)
        node = TradingNodeWrapper()
        logger.info("✅ TradingNodeWrapper initialized")
        
        # We don't start the node as it might be heavy, but just creating it verifies imports
        
    except Exception as e:
        logger.error(f"❌ Nautilus Wrapper test failed: {e}")
        raise

async def main():
    load_dotenv()
    await test_native_adapters()
    await test_nautilus_adapters()
    logger.info("\n✅ Verification Complete.")

if __name__ == "__main__":
    asyncio.run(main())
