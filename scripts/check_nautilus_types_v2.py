from nautilus_trader.model.identifiers import InstrumentId
from nautilus_trader.model.data import BarType
from nautilus_trader.model.enums import PriceType, AggregationSource

print("--- InstrumentId Tests ---")
examples = ["SBIN.NSE", "SBIN-EQ.NSE", "NSE:SBIN.EQUITY", "SBIN-EQ.NSE-EQUITY"]
for ex in examples:
    try:
        iid = InstrumentId.from_str(ex)
        print(f"✅ '{ex}' -> {iid}")
    except Exception as e:
        print(f"❌ '{ex}' failed: {e}")

print("\n--- PriceType Values ---")
for pt in PriceType:
    print(f"- {pt}")

print("\n--- AggregationSource Values ---")
for src in AggregationSource:
    print(f"- {src}")

print("\n--- BarType Test ---")
test_bt = "SBIN.NSE-1-MINUTE-MID-EXTERNAL"
try:
    bt = BarType.from_str(test_bt)
    print(f"✅ BarType '{test_bt}' OK")
except Exception as e:
    print(f"❌ BarType '{test_bt}' failed: {e}")
