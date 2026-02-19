import sys
import os
sys.path.append(os.getcwd())
from src.adapters.nautilus.config import AngelOneDataClientConfig

print("Testing AngelOneDataClientConfig with instrument_provider...")
try:
    config = AngelOneDataClientConfig(instrument_provider="TEST")
    print("✅ Success!")
except Exception as e:
    print(f"❌ Failed: {e}")
