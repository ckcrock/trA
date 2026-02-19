from src.adapters.nautilus.config import AngelOneDataClientConfig

print("Testing AngelOneDataClientConfig with keyword argument...")
try:
    config = AngelOneDataClientConfig(api_key="TEST")
    print(f"✅ Success: api_key={config.api_key}")
except Exception as e:
    print(f"❌ Failed: {e}")
