from nautilus_trader.config import BacktestEngineConfig
from nautilus_trader.model.identifiers import TraderId

print("Testing attribute assignment...")
try:
    config = BacktestEngineConfig(trader_id=TraderId("BACKTESTER-001"))
    config.log_level = "INFO"
    print(f"✅ Assigned log_level: {config.log_level}")
except Exception as e:
    print(f"❌ Failed assignment: {e}")

print("\nTesting other fields...")
fields = ['instance_id', 'user_id', 'log_level_stdout']
for field in fields:
    try:
        setattr(config, field, "TEST")
        print(f"✅ Assigned {field}")
    except Exception as e:
        print(f"❌ Failed {field}: {e}")
