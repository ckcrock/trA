"""
Live Nautilus run using Angel One adapter factories.

This script is intentionally SAFE MODE by default:
- Data client is configured.
- No execution client is configured.
- Strategy can consume live bars but no broker order routing is enabled.
"""

import argparse
import asyncio
import logging
import os
import sys
from typing import Optional

from dotenv import load_dotenv

# Path setup
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("LiveNautilus")

try:
    from nautilus_trader.live.node import TradingNode
    from nautilus_trader.config import TradingNodeConfig
    from nautilus_trader.live.config import RoutingConfig
    from nautilus_trader.model.identifiers import TraderId, InstrumentId, Symbol
    from nautilus_trader.model.instruments import Equity
    from nautilus_trader.model.objects import Price, Quantity, Currency
    NAUTILUS_AVAILABLE = True
except ImportError as e:
    logger.error("Nautilus import error: %s", e)
    NAUTILUS_AVAILABLE = False

from src.adapters.nautilus.config import AngelOneDataClientConfig
from src.adapters.nautilus.factories import AngelOneDataClientFactory
from src.api.dependencies import get_symbol_resolver
from src.strategies.nautilus.ema_cross import EMACross, EMACrossConfig

logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("websocket").setLevel(logging.INFO)


def _normalized_instrument_id(instrument: str, exchange: str) -> str:
    exchange = exchange.strip().upper()
    text = instrument.strip().upper()
    if "." in text:
        return text
    if "-" not in text:
        text = f"{text}-EQ"
    return f"{text}.{exchange}"


def _to_price_increment(raw: object) -> Price:
    try:
        value = float(raw)
    except (TypeError, ValueError):
        value = 0.05

    # Angel master often stores paise-like increments for cash equities.
    if value >= 1:
        value = value / 100.0
    if value <= 0:
        value = 0.05
    return Price.from_str(f"{value:.4f}".rstrip("0").rstrip("."))


def _price_precision_from_increment(price_increment: Price) -> int:
    precision = getattr(price_increment, "precision", None)
    if isinstance(precision, int):
        return precision
    return 2


def _to_lot_size(raw: object) -> Quantity:
    try:
        value = int(float(raw))
    except (TypeError, ValueError):
        value = 1
    return Quantity.from_int(max(1, value))


def _build_equity_instrument(instrument_id_str: str, symbol_info: dict) -> Equity:
    symbol_part = instrument_id_str.split(".", 1)[0]
    price_increment = _to_price_increment(symbol_info.get("tick_size", "0.05"))
    return Equity(
        instrument_id=InstrumentId.from_str(instrument_id_str),
        raw_symbol=Symbol(symbol_part),
        currency=Currency.from_str("INR"),
        price_precision=_price_precision_from_increment(price_increment),
        price_increment=price_increment,
        lot_size=_to_lot_size(symbol_info.get("lotsize", 1)),
        ts_event=0,
        ts_init=0,
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Nautilus live strategy with Angel One data adapter")
    parser.add_argument("--duration", type=int, default=120, help="Run duration in seconds")
    parser.add_argument("--instrument", type=str, default="SBIN-EQ", help="Instrument symbol with series, e.g. SBIN-EQ")
    parser.add_argument("--exchange", type=str, default="NSE", help="Exchange segment, e.g. NSE")
    parser.add_argument("--trader-id", type=str, default="LIVE-TEST-001", help="Nautilus trader id (must contain '-')")
    parser.add_argument("--fast-period", type=int, default=5, help="Fast EMA period")
    parser.add_argument("--slow-period", type=int, default=10, help="Slow EMA period")
    parser.add_argument("--qty", type=int, default=1, help="Strategy quantity")
    return parser.parse_args()


async def main():
    if not NAUTILUS_AVAILABLE:
        raise RuntimeError("Nautilus Trader is not installed")

    args = _parse_args()
    load_dotenv()

    trader_id = args.trader_id.strip()
    if "-" not in trader_id:
        raise ValueError("Invalid --trader-id: must contain '-' (example: LIVE-TEST-001)")

    instrument_id_str = _normalized_instrument_id(args.instrument, args.exchange)
    symbol_part, exchange_part = instrument_id_str.split(".", 1)

    resolver = get_symbol_resolver()
    symbol_info: Optional[dict] = resolver.resolve_by_symbol(symbol_part, exchange_part)
    if not symbol_info:
        raise RuntimeError(
            f"Could not resolve instrument '{instrument_id_str}' from symbol catalog. "
            "Refresh catalog or pass a valid instrument/exchange."
        )

    logger.info("Resolved %s token=%s", instrument_id_str, symbol_info.get("token"))

    data_config = AngelOneDataClientConfig(
        routing=RoutingConfig(default=False, venues=frozenset([exchange_part])),
    )

    node_config = TradingNodeConfig(
        trader_id=TraderId(trader_id),
        data_clients={"ANGELONE": data_config},
    )
    node = TradingNode(config=node_config)

    if hasattr(node, "add_data_client_factory"):
        node.add_data_client_factory("ANGELONE", AngelOneDataClientFactory)
    elif hasattr(node, "register_data_client_factory"):
        node.register_data_client_factory("ANGELONE", AngelOneDataClientFactory)
    else:
        raise RuntimeError("TradingNode does not support known data client factory registration methods")

    instrument = _build_equity_instrument(instrument_id_str, symbol_info)
    node.kernel.data_engine.process(instrument)

    bar_type_str = f"{instrument_id_str}-1-MINUTE-MID-EXTERNAL"
    strategy = EMACross(
        EMACrossConfig(
            instrument_id=instrument_id_str,
            bar_type=bar_type_str,
            fast_period=args.fast_period,
            slow_period=args.slow_period,
            quantity=args.qty,
        ),
    )
    node.trader.add_strategy(strategy)

    logger.warning("SAFE MODE active: no execution clients configured, no broker orders will be sent.")
    node.build()
    node.run()

    try:
        logger.info("Running for %ss: instrument=%s bar_type=%s", args.duration, instrument_id_str, bar_type_str)
        await asyncio.sleep(max(1, args.duration))
    finally:
        logger.info("Stopping node...")
        node.stop()


if __name__ == "__main__":
    asyncio.run(main())
