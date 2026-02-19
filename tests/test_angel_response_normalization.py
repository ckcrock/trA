import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.adapters.angel.data_client import AngelDataClient
from src.adapters.angel.execution_client import AngelExecutionClient
from src.adapters.angel.response_normalizer import (
    extract_order_id,
    normalize_smartapi_response,
)


@pytest.mark.parametrize(
    "raw,expected_ok",
    [
        ({"status": True, "data": {"x": 1}}, True),
        ({"success": True, "data": {"x": 1}}, True),
        ({"data": {"x": 1}}, True),
        ({"status": False, "message": "bad"}, False),
        ("ORD123", True),
        (None, False),
    ],
)
def test_normalize_smartapi_response_shapes(raw, expected_ok):
    normalized = normalize_smartapi_response(raw)
    assert normalized["ok"] is expected_ok
    assert "data" in normalized
    assert "message" in normalized


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("ABC123", "ABC123"),
        ({"data": {"orderid": "ABC123"}}, "ABC123"),
        ({"data": {"orderId": "ABC123"}}, "ABC123"),
        ({"order_id": "ABC123"}, "ABC123"),
        ({}, None),
    ],
)
def test_extract_order_id_variants(raw, expected):
    assert extract_order_id(raw) == expected


def test_execution_place_order_accepts_string_or_dict_order_id():
    auth = MagicMock()
    auth.ensure_authenticated.return_value = True
    rate = MagicMock()
    rate.acquire_async = AsyncMock()

    smart_api = MagicMock()
    auth.get_smart_api_client.return_value = smart_api

    client = AngelExecutionClient(auth, rate)

    smart_api.placeOrder.return_value = "ORD-1"
    result1 = asyncio.run(
        client.place_order(
            trading_symbol="SBIN-EQ",
            symbol_token="3045",
            exchange="NSE",
            transaction_type="BUY",
            quantity=1,
        )
    )
    assert result1 == "ORD-1"

    smart_api.placeOrder.return_value = {"status": True, "data": {"orderid": "ORD-2"}}
    result2 = asyncio.run(
        client.place_order(
            trading_symbol="SBIN-EQ",
            symbol_token="3045",
            exchange="NSE",
            transaction_type="BUY",
            quantity=1,
        )
    )
    assert result2 == "ORD-2"


def test_data_client_quote_and_ltp_use_normalized_response():
    auth = MagicMock()
    auth.ensure_authenticated.return_value = True
    rate = MagicMock()
    rate.acquire_async = AsyncMock()

    smart_api = MagicMock()
    auth.get_smart_api_client.return_value = smart_api

    client = AngelDataClient(auth, rate)

    smart_api.ltpData.return_value = {"data": {"ltp": 501.25}}
    ltp = asyncio.run(client.get_ltp(exchange="NSE", symbol_token="3045", trading_symbol="SBIN-EQ"))
    assert ltp == 501.25

    smart_api.getMarketData.return_value = {"data": {"fetched": [{"ltp": 502.0, "symbolToken": "3045"}]}}
    quote = asyncio.run(client.get_quote(exchange="NSE", symbol_token="3045"))
    assert quote["symbolToken"] == "3045"
