import pandas as pd

from src.catalog.symbol_resolver import SymbolResolver


def test_resolve_by_token_prefers_requested_exchange():
    resolver = SymbolResolver(cache_dir="data/catalog/")
    resolver.instruments_df = pd.DataFrame(
        [
            {"token": "3045", "symbol": "SBIN-EQ", "exch_seg": "NSE"},
            {"token": "3045", "symbol": "SBIN24FEBFUT", "exch_seg": "NFO"},
        ]
    )

    nfo = resolver.resolve_by_token("3045", exchange="NFO")
    assert nfo is not None
    assert nfo["exch_seg"] == "NFO"


def test_resolve_by_token_falls_back_across_exchanges():
    resolver = SymbolResolver(cache_dir="data/catalog/")
    resolver.instruments_df = pd.DataFrame(
        [
            {"token": "9999", "symbol": "TEST-BSE", "exch_seg": "BSE"},
        ]
    )

    result = resolver.resolve_by_token("9999")
    assert result is not None
    assert result["exch_seg"] == "BSE"
