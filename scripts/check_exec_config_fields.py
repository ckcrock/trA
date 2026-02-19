from nautilus_trader.config import LiveExecClientConfig
print("Fields in LiveExecClientConfig:")
for k in LiveExecClientConfig.__annotations__.keys():
    print(f"- {k}")
