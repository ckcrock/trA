import sys
import os
sys.path.append(os.getcwd())
from src.adapters.nautilus.config import AngelOneDataClientConfig

print("Testing AngelOneDataClientConfig with keyword argument...")
try:
    config = AngelOneDataClientConfig(api_key="TEST")
    print("✅ Success!")
except Exception as e:
    print(f"❌ Failed: {e}")
