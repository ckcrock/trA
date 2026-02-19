import asyncio
from unittest.mock import AsyncMock, MagicMock

import pandas as pd

from src.adapters.angel.data_client import AngelDataClient
from src.adapters.angel.execution_client import AngelExecutionClient
from src.bridge.data_bridge import DataBridge


def test_data_bridge_rejects_invalid_tick_payload():
    bridge = DataBridge(max_queue_size=10)

    async def _run():
        await bridge.start()
        bridge.submit_tick({"symbol": "SBIN-EQ"})  # missing token + price fields
        await asyncio.sleep(0.05)
        stats = bridge.get_stats()
        await bridge.stop()
        return stats

    stats = asyncio.run(_run())
    assert stats["ticks_received"] == 0
    assert stats["ticks_dropped"] >= 1


def test_historical_continuity_summary_detects_gaps_and_duplicates():
    df = pd.DataFrame(
        {
            "timestamp": pd.to_datetime(
                [
                    "2026-01-01 09:15:00",
                    "2026-01-01 09:16:00",
                    "2026-01-01 09:16:00",
                    "2026-01-01 09:25:00",  # gap for ONE_MINUTE
                ]
            ),
            "open": [1, 1, 1, 1],
            "high": [1, 1, 1, 1],
            "low": [1, 1, 1, 1],
            "close": [1, 1, 1, 1],
            "volume": [1, 1, 1, 1],
        }
    )
    summary = AngelDataClient._continuity_summary(df, "ONE_MINUTE")
    assert summary["gap_count"] >= 1
    assert summary["duplicate_count"] >= 1


def test_execution_client_rejects_invalid_order_inputs():
    auth = MagicMock()
    auth.ensure_authenticated.return_value = True
    auth.get_smart_api_client.return_value = MagicMock()
    limiter = MagicMock()
    limiter.acquire_async = AsyncMock()

    client = AngelExecutionClient(auth, limiter)
    order_id = asyncio.run(
        client.place_order(
            trading_symbol="SBIN-EQ",
            symbol_token="BAD_TOKEN",
            exchange="NSE",
            transaction_type="BUY",
            quantity=1,
            order_type="MARKET",
            product_type="INTRADAY",
        )
    )
    assert order_id is None

