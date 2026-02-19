from nautilus_trader.config import LiveDataClientConfig
import inspect

print("--- LiveDataClientConfig Init ---")
try:
    print(inspect.signature(LiveDataClientConfig.__init__))
except Exception as e:
    print(f"Error signature: {e}")
