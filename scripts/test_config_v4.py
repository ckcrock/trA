from nautilus_trader.config import BacktestEngineConfig
from nautilus_trader.model.identifiers import TraderId

print(f"Has from_dict: {hasattr(BacktestEngineConfig, 'from_dict')}")

print("\nTesting positional arguments...")
try:
    # Based on annotations: trader_id, instance_id, user_id, log_level
    config = BacktestEngineConfig(TraderId("BACKTESTER-001"), "001", "USER", "INFO")
    print("✅ Success with positional arguments!")
    print(f"TraderId: {config.trader_id}")
    print(f"LogLevel: {config.log_level}")
except Exception as e:
    print(f"❌ Failed positional: {e}")

if hasattr(BacktestEngineConfig, "from_dict"):
    print("\nTesting from_dict...")
    try:
        config = BacktestEngineConfig.from_dict({
            "trader_id": "BACKTESTER-001",
            "log_level": "INFO"
        })
        print("✅ Success with from_dict!")
    except Exception as e:
        print(f"❌ Failed from_dict: {e}")
