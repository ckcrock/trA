from nautilus_trader.config import BacktestEngineConfig
import inspect

print("--- BacktestEngineConfig Signature ---")
try:
    print(inspect.signature(BacktestEngineConfig.__init__))
except Exception as e:
    print(f"Error signature: {e}")

print("\n--- Init Doc ---")
print(BacktestEngineConfig.__init__.__doc__)
