"""
Nautilus LiveDataClient for Angel One.
"""

import asyncio
from datetime import datetime, timezone
from typing import Optional, Dict

try:
    from nautilus_trader.live.data_client import LiveMarketDataClient
    from nautilus_trader.model.identifiers import Venue, ClientId, InstrumentId
    from nautilus_trader.model.data import QuoteTick, BarType, Bar
    from nautilus_trader.model.objects import Price, Quantity
    from nautilus_trader.common.component import MessageBus, Clock, Logger
    from nautilus_trader.cache.cache import Cache
    from nautilus_trader.data.messages import (
        SubscribeBars,
        SubscribeQuoteTicks,
        RequestBars,
        RequestInstrument,
        RequestInstruments,
    )
    NAUTILUS_AVAILABLE = True
except ImportError:
    NAUTILUS_AVAILABLE = False
    # Dummy classes for type hinting
    class LiveMarketDataClient: pass
    class Venue: pass
    class ClientId: pass
    class InstrumentId: pass
    class QuoteTick: pass
    class BarType: pass
    class Bar: pass
    class Price: pass
    class Quantity: pass
    class MessageBus: pass
    class Clock: pass
    class Cache: pass
    class Logger: pass
    class SubscribeBars: pass
    class SubscribeQuoteTicks: pass
    class RequestBars: pass
    class RequestInstrument: pass
    class RequestInstruments: pass


from src.adapters.angel.data_client import AngelDataClient
from src.adapters.angel.websocket_client import AngelWebSocketClient
from .config import AngelOneDataClientConfig
from .parsing import parse_bar, parse_quote_tick
from .providers import AngelOneInstrumentProvider

class AngelOneDataClient(LiveMarketDataClient):
    """
    Angel One Data Client for NautilusTrader.
    Wraps AngelDataClient (REST) and AngelWebSocketClient (WS).
    """
    
    def __init__(
        self,
        loop: asyncio.AbstractEventLoop,
        client: AngelDataClient,
        ws_client: AngelWebSocketClient,
        msgbus: MessageBus,
        cache: Cache,
        clock: Clock,
        instrument_provider: AngelOneInstrumentProvider,
        config: AngelOneDataClientConfig,
    ):
        if not NAUTILUS_AVAILABLE:
            return

        super().__init__(
            loop=loop,
            client_id=ClientId("ANGELONE-DATA"),
            venue=Venue("ANGELONE"),
            msgbus=msgbus,
            cache=cache,
            clock=clock,
            instrument_provider=instrument_provider,
            config=config,
        )
        
        self._http = client
        self._ws = ws_client
        self._provider = instrument_provider
        self._config = config
        
        # Register callback for WebSocket ticks
        # Note: WS callbacks run in a separate thread, so we must use loop.call_soon_threadsafe
        self._ws.register_callback(self._on_ws_tick_threadsafe)
        self._subscription_map: Dict[str, str] = {}  # token -> instrument_id
        # Bar subscription state keyed by str(bar_type)
        self._bar_subscriptions: Dict[str, Dict[str, object]] = {}
        self._bar_subscriptions_by_instrument: Dict[str, set[str]] = {}

    @staticmethod
    def _bar_type_to_interval(bar_type: BarType) -> str:
        text = str(bar_type).upper()
        if "-1-MINUTE-" in text:
            return "ONE_MINUTE"
        if "-3-MINUTE-" in text:
            return "THREE_MINUTE"
        if "-5-MINUTE-" in text:
            return "FIVE_MINUTE"
        if "-10-MINUTE-" in text:
            return "TEN_MINUTE"
        if "-15-MINUTE-" in text:
            return "FIFTEEN_MINUTE"
        if "-30-MINUTE-" in text:
            return "THIRTY_MINUTE"
        if "-1-HOUR-" in text:
            return "ONE_HOUR"
        if "-1-DAY-" in text:
            return "ONE_DAY"
        return "ONE_MINUTE"

    @classmethod
    def _bar_type_to_seconds(cls, bar_type: BarType) -> int:
        interval = cls._bar_type_to_interval(bar_type)
        return {
            "ONE_MINUTE": 60,
            "THREE_MINUTE": 180,
            "FIVE_MINUTE": 300,
            "TEN_MINUTE": 600,
            "FIFTEEN_MINUTE": 900,
            "THIRTY_MINUTE": 1800,
            "ONE_HOUR": 3600,
            "ONE_DAY": 86400,
        }.get(interval, 60)

    @staticmethod
    def _extract_exchange_from_instrument_id(instrument_id: object) -> str:
        text = str(instrument_id or "").strip()
        if "." not in text:
            return ""
        return text.rsplit(".", 1)[-1].strip().upper()

    @staticmethod
    def _normalize_exchange_segment(raw: str) -> str:
        value = str(raw or "").strip().upper()
        mapping = {
            "ANGELONE": "NSE",
            "NSE_CM": "NSE",
            "NSE_EQ": "NSE",
            "NSE_FO": "NFO",
            "BSE_CM": "BSE",
            "BSE_EQ": "BSE",
            "BSE_FO": "BSE",
            "MCX_FO": "MCX",
            "NCO": "NCX_FO",
            "CDS": "CDE_FO",
        }
        return mapping.get(value, value or "NSE")

    @classmethod
    def _instrument_exchange(cls, instrument: object, instrument_id: object) -> str:
        by_id = cls._extract_exchange_from_instrument_id(instrument_id)
        if by_id:
            return cls._normalize_exchange_segment(by_id)

        venue = getattr(getattr(instrument, "venue", None), "value", None)
        if venue is None:
            venue = getattr(instrument, "venue", None)
        return cls._normalize_exchange_segment(str(venue or "NSE"))

    @staticmethod
    def _as_datetime(value: object) -> Optional[datetime]:
        if value is None:
            return None

        if isinstance(value, datetime):
            return value if value.tzinfo else value.replace(tzinfo=timezone.utc)

        if hasattr(value, "to_pydatetime"):
            try:
                dt = value.to_pydatetime()
                return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
            except Exception:
                pass

        # Handle unix timestamps across seconds/ms/us/ns.
        try:
            ts = int(value)
            if ts > 10**16:      # ns
                sec = ts / 1_000_000_000.0
            elif ts > 10**13:    # us
                sec = ts / 1_000_000.0
            elif ts > 10**10:    # ms
                sec = ts / 1_000.0
            else:                # sec
                sec = float(ts)
            return datetime.fromtimestamp(sec, tz=timezone.utc)
        except Exception:
            pass

        try:
            text = str(value).strip()
            if text.endswith("Z"):
                text = text[:-1] + "+00:00"
            dt = datetime.fromisoformat(text)
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except Exception:
            return None

    @staticmethod
    def _price_from_tick(raw: object) -> float:
        try:
            value = float(raw)
        except (TypeError, ValueError):
            return 0.0
        # Angel WS commonly sends paise values as integers.
        if abs(value) >= 1000 and float(int(value)) == value:
            return value / 100.0
        return value

    @staticmethod
    def _timestamp_ns_from_tick(tick: dict) -> int:
        raw = (
            tick.get("exchange_timestamp")
            or tick.get("last_traded_timestamp")
            or tick.get("timestamp")
        )
        if raw is None:
            return 0
        try:
            ts = int(float(raw))
            if ts > 10**16:      # ns
                return ts
            if ts > 10**13:      # us
                return ts * 1000
            if ts > 10**10:      # ms
                return ts * 1_000_000
            return ts * 1_000_000_000  # sec
        except (TypeError, ValueError):
            return 0

    @staticmethod
    def _trade_qty_from_tick(tick: dict) -> int:
        raw = tick.get("last_traded_quantity") or tick.get("ltq") or 0
        try:
            return max(0, int(float(raw)))
        except (TypeError, ValueError):
            return 0

    @staticmethod
    def _make_price(instrument: object, value: float):
        if hasattr(instrument, "make_price"):
            return instrument.make_price(value)
        return Price.from_str(str(value))

    @staticmethod
    def _make_qty(instrument: object, value: int):
        if hasattr(instrument, "make_qty"):
            return instrument.make_qty(value)
        return Quantity.from_int(max(0, int(value)))

    def _build_live_bar(self, sub: Dict[str, object], state: Dict[str, object]) -> Optional[Bar]:
        try:
            instrument = sub["instrument"]
            return Bar(
                bar_type=sub["bar_type"],
                open=self._make_price(instrument, float(state["open"])),
                high=self._make_price(instrument, float(state["high"])),
                low=self._make_price(instrument, float(state["low"])),
                close=self._make_price(instrument, float(state["close"])),
                volume=self._make_qty(instrument, int(state["volume"])),
                ts_event=int(state["ts_event"]),
                ts_init=int(state["ts_init"]),
            )
        except Exception as e:
            self._log.error(f"Failed building live bar: {e}")
            return None

    def _broker_token(self, instrument_id: object, instrument: object) -> str:
        token = str(getattr(instrument, "broker_symbol_token", "")).strip()
        if token:
            return token
        if hasattr(self._provider, "get_broker_token"):
            mapped = self._provider.get_broker_token(str(instrument_id))
            token = str(mapped or "").strip()
        return token

    def _ensure_ws_subscription(self, instrument_id: object, instrument: object):
        token = self._broker_token(instrument_id, instrument)
        exchange_seg = self._instrument_exchange(instrument, instrument_id)

        if not token:
            self._log.error(f"Instrument missing broker token: {instrument_id}")
            return

        if token in self._subscription_map:
            return

        self._ws.subscribe(mode=2, token_list=[{"exchangeType": exchange_seg, "tokens": [token]}])
        self._subscription_map[token] = str(instrument_id)
        self._log.info(f"Subscribed to {instrument_id} token={token} exchange={exchange_seg}")

    def _update_live_bar_subscriptions(self, tick: dict):
        token = str(tick.get("token") or tick.get("symbol_token") or "").strip()
        if not token:
            return

        instrument_id = self._subscription_map.get(token)
        if not instrument_id and hasattr(self._provider, "find_by_token"):
            ref = self._provider.find_by_token(token)
            instrument_id = str(getattr(ref, "instrument_id", "")) if ref else ""
        if not instrument_id:
            return

        sub_keys = self._bar_subscriptions_by_instrument.get(instrument_id, set())
        if not sub_keys:
            return

        last_price = self._price_from_tick(
            tick.get("last_traded_price") or tick.get("ltp") or tick.get("last_price")
        )
        if last_price <= 0:
            bid = self._price_from_tick(tick.get("best_bid_price") or 0)
            ask = self._price_from_tick(tick.get("best_ask_price") or 0)
            if bid > 0 and ask > 0:
                last_price = (bid + ask) / 2.0
        if last_price <= 0:
            return

        ts_event = self._timestamp_ns_from_tick(tick) or self._clock.timestamp_ns()
        qty = self._trade_qty_from_tick(tick)
        ts_init = self._clock.timestamp_ns()

        for key in list(sub_keys):
            sub = self._bar_subscriptions.get(key)
            if not sub:
                continue

            interval_ns = int(sub["interval_secs"]) * 1_000_000_000
            bucket_ns = (ts_event // interval_ns) * interval_ns
            state = sub.get("current")

            if state is None:
                sub["current"] = {
                    "open": last_price,
                    "high": last_price,
                    "low": last_price,
                    "close": last_price,
                    "volume": qty,
                    "ts_event": bucket_ns,
                    "ts_init": ts_init,
                }
                continue

            if int(state["ts_event"]) != int(bucket_ns):
                bar = self._build_live_bar(sub, state)
                if bar is not None:
                    self._handle_data(bar)
                sub["current"] = {
                    "open": last_price,
                    "high": last_price,
                    "low": last_price,
                    "close": last_price,
                    "volume": qty,
                    "ts_event": bucket_ns,
                    "ts_init": ts_init,
                }
                continue

            state["high"] = max(float(state["high"]), last_price)
            state["low"] = min(float(state["low"]), last_price)
            state["close"] = last_price
            state["volume"] = int(state["volume"]) + qty

    def _flush_live_bars(self):
        for sub in self._bar_subscriptions.values():
            state = sub.get("current")
            if not state:
                continue
            bar = self._build_live_bar(sub, state)
            if bar is not None:
                self._handle_data(bar)
            sub["current"] = None

    async def _connect(self):
        """Connect to data services."""
        if not self._ws.is_connected:
            self._log.info("Connecting WebSocket...")
            self._ws.connect_in_thread()
            
    async def _disconnect(self):
        """Disconnect data services."""
        self._flush_live_bars()
        self._ws.close()

    async def _subscribe_bars(self, command: SubscribeBars):
        bar_type = command.bar_type
        instrument_id = getattr(bar_type, "instrument_id", None)
        if instrument_id is None:
            self._log.error(f"SubscribeBars missing instrument_id: {bar_type}")
            return

        instrument = self._provider.find(str(instrument_id))
        if not instrument:
            self._log.error(f"Instrument not found for bar subscription: {instrument_id}")
            return

        key = str(bar_type)
        self._bar_subscriptions[key] = {
            "bar_type": bar_type,
            "instrument_id": str(instrument_id),
            "instrument": instrument,
            "interval_secs": self._bar_type_to_seconds(bar_type),
            "current": None,
        }
        self._bar_subscriptions_by_instrument.setdefault(str(instrument_id), set()).add(key)

        try:
            self._ensure_ws_subscription(instrument_id, instrument)
            self._log.info(f"Subscribed bars for {key}")
        except Exception as e:
            self._log.error(f"Failed subscribing bars for {key}: {e}")

    async def _subscribe_quote_ticks(self, command: SubscribeQuoteTicks):
        """Subscribe to live quotes."""
        instrument_id = command.instrument_id
        instrument = self._provider.find(str(instrument_id))
        if not instrument:
            self._log.error(f"Instrument not found: {instrument_id}")
            return

        try:
            self._ensure_ws_subscription(instrument_id, instrument)
        except Exception as e:
            self._log.error(f"Failed to subscribe quote ticks for {instrument_id}: {e}")

    def _on_ws_tick_threadsafe(self, tick: dict):
        """Handle tick from WebSocket (called from WS thread)."""
        self._loop.call_soon_threadsafe(self._process_tick, tick)
        
    def _process_tick(self, tick: dict):
        """Process tick in event loop."""
        try:
            quote_tick = parse_quote_tick(tick, self._provider, self._clock.timestamp_ns())
            if quote_tick:
                self._handle_data(quote_tick)
            self._update_live_bar_subscriptions(tick)
        except Exception as e:
            self._log.error(f"Error processing tick: {e}")

    async def _request_bars(self, request: RequestBars):
        """Request historical bars."""
        bar_type = request.bar_type
        start = self._as_datetime(request.start)
        end = self._as_datetime(request.end)
        if start is None or end is None:
            self._log.warning(f"Invalid bar request window start={request.start} end={request.end}")
            return

        # Validate instrument
        instrument_id = getattr(bar_type, "instrument_id", None)
        if instrument_id is None:
            return

        instrument = self._provider.find(str(instrument_id))
        if not instrument:
            return

        # Fetch from HTTP client
        interval = self._bar_type_to_interval(bar_type)
        exchange = self._instrument_exchange(instrument, instrument_id)
        token = self._broker_token(instrument_id, instrument)
        if not token:
            self._log.error(f"Cannot request bars without broker token for {instrument_id}")
            return
        
        bars_df = await self._http.get_historical_data(
            symbol_token=token,
            exchange=exchange,
            interval=interval,
            from_date=start,
            to_date=end
        )
        
        if bars_df is None or bars_df.empty:
            return

        # Parse and publish
        ts_init = self._clock.timestamp_ns()
        published = 0
        for _, row in bars_df.iterrows():
            candle = [
                row.get("timestamp"),
                row.get("open"),
                row.get("high"),
                row.get("low"),
                row.get("close"),
                row.get("volume", 0),
            ]
            bar = parse_bar(bar_type, candle, instrument, ts_init)
            if bar is not None:
                self._handle_data(bar)
                published += 1

        self._log.info(f"Published {published} historical bars for {instrument_id}")

    async def _request_instrument(self, request: RequestInstrument):
        instrument = self._provider.find(str(request.instrument_id))
        if instrument is None:
            self._log.warning(f"Instrument not found for request: {request.instrument_id}")

    async def _request_instruments(self, request: RequestInstruments):
        # Not implemented as bulk request path for Angel catalog in live mode.
        return
