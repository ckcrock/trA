from nautilus_trader.model.instruments import Equity
import inspect

print("--- Equity Docstring ---")
print(Equity.__doc__)

try:
    from nautilus_trader.model.identifiers import InstrumentId
    from nautilus_trader.model.objects import Price, Quantity
    from nautilus_trader.model.identifiers import Venue
    from nautilus_trader.model.objects import Currency
    
    print("\nAttempting to instantiate Equity to test params...")
    # Test without 'venue'
    instrument_id = InstrumentId.from_str("SBIN-EQ.NSE")
    inst = Equity(
        instrument_id=instrument_id,
        raw_symbol="SBIN",
        # venue=Venue("NSE"), # Replaced by instrument_id's venue in some versions
        price_increment=Price.from_str("0.05"),
        base_currency=Currency.from_str("INR"),
        quote_currency=Currency.from_str("INR"),
        lot_size=Quantity.from_str("1"),
        ts_event=0,
        ts_init=0
    )
    print("✅ Successfully instantiated Equity without 'venue' argument.")
except Exception as e:
    print(f"❌ Failed to instantiate: {e}")
