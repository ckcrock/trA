from nautilus_trader.config import LiveDataClientConfig

print("Testing LiveDataClientConfig with no arguments...")
try:
    config = LiveDataClientConfig()
    print("✅ Success with default init")
except Exception as e:
    print(f"❌ Failed default init: {e}")
