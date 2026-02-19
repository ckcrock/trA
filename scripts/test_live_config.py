from nautilus_trader.config import LiveDataClientConfig

print("Testing LiveDataClientConfig with keyword argument...")
try:
    # Try instrument_provider_id
    config = LiveDataClientConfig(instrument_provider_id="TEST")
    print("✅ Success with instrument_provider_id")
except Exception as e:
    print(f"❌ Failed with instrument_provider_id: {e}")

try:
    # Try positional
    config = LiveDataClientConfig("TEST")
    print("✅ Success with positional 'TEST'")
except Exception as e:
    print(f"❌ Failed with positional: {e}")

# Check annotations again
print("\nAnnotations:")
print(LiveDataClientConfig.__annotations__)
