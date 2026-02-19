from nautilus_trader.config import BacktestEngineConfig
from nautilus_trader.model.identifiers import TraderId
import os
import nautilus_trader

with open("config_results.txt", "w", encoding="utf-8") as f:
    f.write("Testing with TraderId object...\n")
    try:
        config = BacktestEngineConfig(trader_id=TraderId("BACKTESTER-001"))
        f.write("✅ Success with TraderId object\n")
    except Exception as e:
        f.write(f"❌ Failed: {e}\n")

    f.write("\nTesting with log_level...\n")
    try:
        config = BacktestEngineConfig(
            trader_id=TraderId("BACKTESTER-001"),
            log_level="INFO"
        )
        f.write("✅ Success with log_level\n")
    except Exception as e:
        f.write(f"❌ Failed: {e}\n")

    # Find examples
    nt_path = os.path.dirname(nautilus_trader.__file__)
    f.write(f"\nNautilus path: {nt_path}\n")
    count = 0
    for root, dirs, files in os.walk(nt_path):
        if "backtest" in root:
            for file in files:
                if file.endswith(".py"):
                    f.write(f"File: {os.path.join(root, file)}\n")
                    count += 1
        if count > 20: break
