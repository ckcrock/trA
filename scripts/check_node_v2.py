from nautilus_trader.backtest.node import BacktestNode
from nautilus_trader.live.node import TradingNode

with open("node_help.txt", "w", encoding="utf-8") as f:
    f.write("--- BacktestNode ---\n")
    f.write(str(BacktestNode.__doc__))
    f.write("\n\n--- TradingNode ---\n")
    f.write(str(TradingNode.__doc__))
