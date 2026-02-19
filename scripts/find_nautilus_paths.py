import importlib
import nautilus_trader
import sys

with open("path_results.txt", "w", encoding="utf-8") as f:
    f.write(f"Nautilus version: {nautilus_trader.__version__}\n")

    test_modules = [
        "nautilus_trader.trading.node",
        "nautilus_trader.node",
        "nautilus_trader.config",
        "nautilus_trader.model.identifiers",
        "nautilus_trader.model.data",
        "nautilus_trader.model.enums",
        "nautilus_trader.model.objects",
        "nautilus_trader.model.instruments",
        "nautilus_trader.model.orders",
        "nautilus_trader.live.execution_client",
        "nautilus_trader.live.data_client",
        "nautilus_trader.common.component",
        "nautilus_trader.indicators.average.ema",
    ]

    for mod in test_modules:
        try:
            importlib.import_module(mod)
            f.write(f"OK: {mod}\n")
        except ImportError as e:
            f.write(f"MISSING: {mod} ({e})\n")

    def check_class(mod_name, class_name):
        try:
            mod = importlib.import_module(mod_name)
            if hasattr(mod, class_name):
                f.write(f"FOUND: {class_name} in {mod_name}\n")
                return True
        except:
            pass
        return False

    check_class("nautilus_trader.node", "TradingNode")
    check_class("nautilus_trader.trading.node", "TradingNode")
    check_class("nautilus_trader.core.nautilus_node", "TradingNode")
