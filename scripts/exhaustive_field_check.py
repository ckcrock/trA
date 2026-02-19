from nautilus_trader.config import LiveDataClientConfig
print("Fields in LiveDataClientConfig:")
for k in LiveDataClientConfig.__annotations__.keys():
    print(f"- {k}")

print("\nTesting keyword init with ONE field at a time...")
fields = list(LiveDataClientConfig.__annotations__.keys())
for field in fields[:5]: # Test first 5
    try:
        config = LiveDataClientConfig(**{field: "TEST" if "str" in str(LiveDataClientConfig.__annotations__[field]) else None})
        print(f"✅ Success with {field}")
    except Exception as e:
        print(f"❌ Failed with {field}: {e}")
