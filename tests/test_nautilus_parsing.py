import pytest

from src.adapters.nautilus import parsing


@pytest.mark.skipif(not parsing.NAUTILUS_AVAILABLE, reason="Nautilus Trader not installed")
def test_parse_quote_tick_from_angel_payload():
    class Provider:
        def find_by_token(self, token: str):
            class Ref:
                instrument_id = "SBIN-EQ.NSE"
            return Ref()

    payload = {
        "token": "3045",
        "exchange_timestamp": 1700000000000,  # ms
        "last_traded_price": 50025,  # paise
        "best_5_buy_data": [{"price": 50020, "quantity": 10}],
        "best_5_sell_data": [{"price": 50030, "quantity": 12}],
    }

    tick = parsing.parse_quote_tick(payload, Provider(), ts_init=1700000000000000000)
    assert tick is not None
    assert tick.instrument_id.value == "SBIN-EQ.NSE"
    assert round(tick.bid_price.as_double(), 2) == 500.20
    assert round(tick.ask_price.as_double(), 2) == 500.30
    assert int(tick.bid_size.as_double()) == 10
    assert int(tick.ask_size.as_double()) == 12


@pytest.mark.skipif(not parsing.NAUTILUS_AVAILABLE, reason="Nautilus Trader not installed")
def test_parse_bar_with_lightweight_instrument_fallback():
    from nautilus_trader.model.data import BarType

    class LightweightRef:
        pass

    bar_type = BarType.from_str("SBIN-EQ.NSE-1-MINUTE-MID-EXTERNAL")
    candle = ["2026-01-01 09:15:00", 100.0, 101.0, 99.0, 100.5, 10]
    bar = parsing.parse_bar(bar_type, candle, LightweightRef(), ts_init=0)
    assert bar is not None
    assert round(bar.open.as_double(), 2) == 100.00
    assert int(bar.volume.as_double()) == 10


@pytest.mark.skipif(not parsing.NAUTILUS_AVAILABLE, reason="Nautilus Trader not installed")
def test_parse_quote_tick_supports_normalized_tick_keys():
    from nautilus_trader.model.identifiers import InstrumentId

    class Provider:
        def find_by_token(self, token: str):
            class Ref:
                instrument_id = InstrumentId.from_str("SBIN-EQ.NSE")
            return Ref()

    payload = {
        "symbol_token": "3045",
        "timestamp": "2026-01-01T09:15:00+00:00",
        "ltp": 50025,
        "bid": 50020,
        "ask": 50030,
        "bid_qty": 15,
        "ask_qty": 18,
    }

    tick = parsing.parse_quote_tick(payload, Provider(), ts_init=1700000000000000000)
    assert tick is not None
    assert tick.instrument_id.value == "SBIN-EQ.NSE"
    assert round(tick.bid_price.as_double(), 2) == 500.20
    assert round(tick.ask_price.as_double(), 2) == 500.30
    assert int(tick.bid_size.as_double()) == 15
    assert int(tick.ask_size.as_double()) == 18
