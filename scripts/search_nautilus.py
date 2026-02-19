import importlib
import pkgutil
import nautilus_trader
import os

with open("search_results.txt", "w", encoding="utf-8") as f:
    f.write(f"Searching for components in NautilusTrader {nautilus_trader.__version__}\n")

    package = nautilus_trader
    for loader, name, is_pkg in pkgutil.walk_packages(package.__path__, package.__name__ + "."):
        try:
            mod = importlib.import_module(name)
            if hasattr(mod, "TradingNode"):
                f.write(f"FOUND TradingNode in {name}\n")
            if hasattr(mod, "BacktestNode"):
                f.write(f"FOUND BacktestNode in {name}\n")
            if hasattr(mod, "ExponentialMovingAverage"):
                f.write(f"FOUND EMA in {name}\n")
            if hasattr(mod, "Strategy"):
                f.write(f"FOUND Strategy in {name}\n")
        except:
            pass
