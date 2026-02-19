from nautilus_trader.backtest.engine import BacktestEngine
with open("engine_help.txt", "w", encoding="utf-8") as f:
    f.write(str(BacktestEngine.__doc__))
