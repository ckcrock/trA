import sys
import os
sys.path.append(os.getcwd())

print("Attempting to import from src.utils.constants...")
try:
    # Importing all classes defined in constants.py
    from src.utils.constants import (
        Exchange, ProductType, OrderType, TransactionType, 
        Variety, Duration, OrderStatus, DataMode, MarketHours, Interval,
        COMMON_TOKENS, TaxRates, RISK_FREE_RATE_INDIA, TRADING_DAYS_PER_YEAR
    )
    print("✅ All expected constants imported successfully.")
except ImportError as e:
    print(f"❌ ImportError: {e}")
except Exception as e:
    print(f"❌ Unexpected Error: {e}")
