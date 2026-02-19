import sys
import os
import traceback
import logging

# Add current CWD to sys.path
cwd = os.getcwd()
sys.path.append(cwd)

logging.basicConfig(level=logging.INFO)

try:
    print("--- 1. Testing Imports ---")
    from src.utils.constants import Exchange
    from src.adapters.angel.auth import AngelAuthManager
    from src.adapters.angel.data_client import AngelDataClient
    from src.adapters.angel.execution_client import AngelExecutionClient
    from src.adapters.angel.rate_limiter import TokenBucketRateLimiter
    from src.adapters.nautilus import NAUTILUS_AVAILABLE
    print(f"✅ Imports Successful. Nautilus Available: {NAUTILUS_AVAILABLE}")

    print("\n--- 2. Testing Instantiation ---")
    
    # Mock Credentials
    auth = AngelAuthManager(
        api_key="test",
        client_code="test", 
        mpin="test", 
        totp_secret="test"
    )
    rate_limiter = TokenBucketRateLimiter(3.0)
    
    data_client = AngelDataClient(auth, rate_limiter)
    print("✅ AngelDataClient Instantiated")
    
    exec_client = AngelExecutionClient(auth, rate_limiter)
    print("✅ AngelExecutionClient Instantiated")
    
    if NAUTILUS_AVAILABLE:
        print("\n--- 3. Testing Nautilus Wrappers ---")
        from src.adapters.nautilus.factories import AngelOneDataClientFactory
        from src.engine.node import TradingNodeWrapper
        
        node = TradingNodeWrapper()
        print("✅ TradingNodeWrapper Instantiated")
        
    print("\n✅ VERIFICATION COMPLETE: ALL SYSTEMS GO")

except Exception:
    traceback.print_exc()
