from nautilus_trader.config import BacktestEngineConfig
from nautilus_trader.model.identifiers import TraderId

print("Testing with TraderId object...")
try:
    config = BacktestEngineConfig(trader_id=TraderId("BACKTESTER-001"))
    print("✅ Success with TraderId object")
except Exception as e:
    print(f"❌ Failed: {e}")

print("\nTesting with log_level...")
try:
    config = BacktestEngineConfig(
        trader_id=TraderId("BACKTESTER-001"),
        log_level="INFO"
    )
    print("✅ Success with log_level")
except Exception as e:
    print(f"❌ Failed: {e}")

# Find examples
import os
import nautilus_trader
nt_path = os.path.dirname(nautilus_trader.__file__)
print(f"\nNautilus path: {nt_path}")
for root, dirs, files in os.walk(nt_path):
    if "backtest" in root and "example" in root:
        for f in files:
            if f.endswith(".py"):
                print(f"Example found: {os.path.join(root, f)}")
