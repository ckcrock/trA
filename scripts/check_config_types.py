import nautilus_trader.config as config
import inspect

def print_params(cls_name):
    try:
        cls = getattr(config, cls_name)
        print(f"--- {cls_name} ---")
        # For Pydantic/Rust models, signature might be tricky, try __annotations__
        if hasattr(cls, "__annotations__"):
            print(cls.__annotations__)
        else:
            print(inspect.signature(cls.__init__))
    except Exception as e:
        print(f"Error {cls_name}: {e}")

print_params("BacktestEngineConfig")
print_params("LogServiceConfig")
print_params("LoggingConfig")
