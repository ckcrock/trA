from nautilus_trader.model.identifiers import InstrumentId, Venue
from nautilus_trader.model.data import BarType
from nautilus_trader.model.enums import PriceType

print("--- InstrumentId Test ---")
try:
    iid = InstrumentId.from_str("SBIN.NSE")
    print(f"✅ 'SBIN.NSE' -> {iid}")
except Exception as e:
    print(f"❌ 'SBIN.NSE' failed: {e}")

try:
    iid = InstrumentId.from_str("NSE:SBIN.EQUITY")
    print(f"✅ 'NSE:SBIN.EQUITY' -> {iid}")
except Exception as e:
    print(f"❌ 'NSE:SBIN.EQUITY' failed: {e}")

print("\n--- PriceType Values ---")
for pt in PriceType:
    print(f"- {pt}")

print("\n--- BarType Test ---")
try:
    # Testing MID price type
    bt = BarType.from_str("SBIN.NSE-1-MINUTE-MID-EXTERNAL")
    print(f"✅ BarType OK: {bt}")
except Exception as e:
    print(f"❌ BarType failed: {e}")
