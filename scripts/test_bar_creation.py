from nautilus_trader.model.data import Bar, BarType
from nautilus_trader.model.identifiers import InstrumentId
from nautilus_trader.model.objects import Price, Quantity

import sys
import os
import nautilus_trader.model.objects as objects
import nautilus_trader.model.data as data
print(f"DEBUG: Objects module file: {objects.__file__}")
print(f"DEBUG: Data module file: {data.__file__}")
print(f"DEBUG: sys.path: {sys.path}")

def test():
    print("--- TESTING BAR CREATION ---")
    bt = BarType.from_str('SBIN-EQ.NSE-1-MINUTE-LAST-INTERNAL')
    iid = InstrumentId.from_str('SBIN-EQ.NSE')
    p = Price.from_str('100.0')
    q = Quantity.from_str('0')

    print(f"BarType: {bt}, type: {type(bt)}")
    print(f"InstrumentId: {iid}, type: {type(iid)}")
    print(f"Price: {p}, type: {type(p)}")
    print(f"Quantity: {q}, type: {type(q)}")

    print("\n1. Testing Positional...")
    try:
        # Bar(bar_type, instrument_id, ts_event, ts_init, open, high, low, close, volume)
        b = Bar(bt, iid, 123456, 123456, p, p, p, p, q)
        print("✅ Positional Success")
    except Exception as e:
        print(f"❌ Positional Fail: {e}")
        import traceback
        traceback.print_exc()

    print("\n3. Testing from_dict with Raw Values...")
    try:
        if hasattr(Bar, 'from_dict'):
            d = {
                "bar_type": bt,
                "instrument_id": iid,
                "ts_event": 123456,
                "ts_init": 123456,
                "open": 10000,
                "high": 10000,
                "low": 10000,
                "close": 10000,
                "volume": 0
            }
            b = Bar.from_dict(d)
            print("✅ from_dict with Raw Values Success")
        else:
            print("⚠️ Bar has no from_dict")
    except Exception as e:
        print(f"❌ from_dict with Raw Values Fail: {e}")

    print("\n5. Testing TradeTick Keywords...")
    try:
        from nautilus_trader.model.data import TradeTick
        # TradeTick(instrument_id, ts_event, ts_init, price, size, aggressor=0)
        t = TradeTick(
            instrument_id=iid,
            ts_event=123456,
            ts_init=123456,
            price=p,
            size=q
        )
        print("✅ TradeTick Keywords Success")
    except Exception as e:
        print(f"❌ TradeTick Keywords Fail: {e}")

if __name__ == "__main__":
    test()
