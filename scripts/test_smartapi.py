from SmartApi import SmartConnect
import logging

logging.basicConfig(level=logging.INFO)

print("--- Testing SmartApi ---")
try:
    obj = SmartConnect(api_key="test_key")
    print(f"✅ SmartConnect Instantiated: {obj}")
except Exception as e:
    print(f"❌ SmartConnect Failed: {e}")
    import traceback
    traceback.print_exc()
