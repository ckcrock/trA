from nautilus_trader.backtest.engine import BacktestEngine
print("--- BacktestEngine Methods ---")
print([m for m in dir(BacktestEngine) if not m.startswith("_")])
