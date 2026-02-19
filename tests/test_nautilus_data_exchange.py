from src.adapters.nautilus.data import AngelOneDataClient


def test_instrument_exchange_prefers_instrument_id_suffix():
    class Instrument:
        class _Venue:
            value = "ANGELONE"

        venue = _Venue()

    exchange = AngelOneDataClient._instrument_exchange(Instrument(), "SBIN-EQ.NFO")
    assert exchange == "NFO"


def test_instrument_exchange_normalizes_angelone_to_nse():
    class Instrument:
        class _Venue:
            value = "ANGELONE"

        venue = _Venue()

    exchange = AngelOneDataClient._instrument_exchange(Instrument(), "SBIN-EQ.ANGELONE")
    assert exchange == "NSE"
