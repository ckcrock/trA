import asyncio
import logging
from datetime import datetime, timezone
from asyncio import Queue, QueueFull
from typing import Callable, List, Dict, Any, Awaitable

try:
    from prometheus_client import Counter, Gauge
    BRIDGE_TICKS_RECEIVED = Counter(
        "bridge_ticks_received_total", "Total ticks received by DataBridge"
    )
    BRIDGE_TICKS_DROPPED = Counter(
        "bridge_ticks_dropped_total", "Total ticks dropped due to queue full"
    )
    BRIDGE_QUEUE_SIZE = Gauge(
        "bridge_queue_size", "Current DataBridge queue size"
    )
    BRIDGE_TICKS_INVALID = Counter(
        "bridge_ticks_invalid_total", "Total malformed ticks dropped by DataBridge"
    )
    PROM_AVAILABLE = True
except ImportError:
    PROM_AVAILABLE = False

logger = logging.getLogger(__name__)

class DataBridge:
    """
    Bridge between threaded WebSocket adapters and async event loop.
    Handles backpressure and broadcast fanout.
    """
    
    def __init__(self, max_queue_size: int = 10000):
        self.queue = Queue(maxsize=max_queue_size)
        self.subscribers: List[Callable[[Dict], Awaitable[None]]] = []  # List of async callbacks
        self.running = False
        self._loop: asyncio.AbstractEventLoop | None = None
        self._processor_task: asyncio.Task | None = None
        self.stats = {
            'ticks_received': 0,
            'ticks_dropped': 0,
            'broadcast_count': 0,
        }

    def _enqueue_tick(self, tick: dict):
        """Runs on the event loop thread to enqueue safely and track drops."""
        if not self._is_valid_tick(tick):
            self.stats['ticks_dropped'] += 1
            if PROM_AVAILABLE:
                BRIDGE_TICKS_INVALID.inc()
            return
        try:
            self.queue.put_nowait(tick)
            self.stats['ticks_received'] += 1
            if PROM_AVAILABLE:
                BRIDGE_TICKS_RECEIVED.inc()
                BRIDGE_QUEUE_SIZE.set(self.queue.qsize())
        except QueueFull:
            self.stats['ticks_dropped'] += 1
            if PROM_AVAILABLE:
                BRIDGE_TICKS_DROPPED.inc()

    @staticmethod
    def _is_valid_tick(tick: dict) -> bool:
        """
        Minimal payload contract for downstream consumers.
        Requires at least token + one price-like field.
        """
        if not isinstance(tick, dict):
            return False
        token = tick.get("token")
        has_price = any(k in tick for k in ("ltp", "last_traded_price", "best_bid_price", "best_ask_price"))
        return token is not None and has_price
    
    def submit_tick(self, tick: dict):
        """
        Thread-safe tick submission from WebSocket thread.
        Non-blocking - drops tick if queue is full.
        Note: Since this is called from a thread, we use call_soon_threadsafe if loop is running,
        or just put into queue if queue is thread-safe (asyncio.Queue is NOT thread-safe for put_nowait from other threads directly safely without loop interaction usually, but here we assum integrated usage).
        
        Actually, for cross-thread submission to asyncio Queue, we need loop.call_soon_threadsafe.
        """
        if self._loop is None:
            logger.warning("Event loop not initialized, cannot submit tick")
            return
        self._loop.call_soon_threadsafe(self._enqueue_tick, tick)
            
    def subscribe(self, callback: Callable[[Dict], Awaitable[None]]):
        """Register an async callback for tick events"""
        self.subscribers.append(callback)
    
    async def start(self):
        """Start the event processing loop"""
        self.running = True
        self._loop = asyncio.get_running_loop()
        self._processor_task = asyncio.create_task(self._process_events())
        logger.info("DataBridge started")
    
    async def stop(self):
        """Stop the event processing loop"""
        self.running = False
        if self._processor_task:
            await self._processor_task
            self._processor_task = None
        self._loop = None
        logger.info("DataBridge stopped")
    
    async def _process_events(self):
        """Main event processing loop"""
        while self.running:
            try:
                # Get tick from queue (with timeout to allow checking running flag)
                try:
                    tick = await asyncio.wait_for(self.queue.get(), timeout=1.0)
                except asyncio.TimeoutError:
                    continue
                
                # Normalize tick data
                normalized_tick = self._normalize_tick(tick)
                
                # Broadcast to all subscribers
                await self._broadcast(normalized_tick)
                
                self.stats['broadcast_count'] += 1
                self.queue.task_done()
                
            except Exception as e:
                logger.error(f"Error processing tick: {e}")
    
    def _normalize_tick(self, raw_tick: dict) -> dict:
        """Normalize tick to standard format"""
        # Angel One WebSocket V2 sends several price fields in paise-like scale.
        def _normalize_price(value: Any) -> float:
            try:
                num = float(value or 0)
                if abs(num) >= 100000:  # Heuristic: raw scaled integer
                    return num / 100.0
                return num
            except (TypeError, ValueError):
                return 0.0

        def _normalize_ts(raw: Any) -> str:
            if raw is None:
                return datetime.now(timezone.utc).isoformat()
            try:
                if isinstance(raw, str):
                    stripped = raw.strip()
                    if stripped.isdigit():
                        raw = float(stripped)
                    else:
                        # Already ISO text.
                        return stripped
                ts_val = float(raw)
                if ts_val > 1e15:  # microseconds (defensive)
                    ts_val = ts_val / 1_000_000.0
                elif ts_val > 1e12:   # milliseconds
                    ts_val = ts_val / 1000.0
                return datetime.fromtimestamp(ts_val, tz=timezone.utc).isoformat()
            except (TypeError, ValueError, OSError):
                return datetime.now(timezone.utc).isoformat()

        # Angel One specific keys to standard keys.
        ltp = _normalize_price(raw_tick.get("ltp", 0) or raw_tick.get("last_traded_price", 0))

        # WebSocket V2 quote payloads typically provide best 5 ladders.
        best_buy = raw_tick.get("best_5_buy_data") or []
        best_sell = raw_tick.get("best_5_sell_data") or []
        best_buy_0 = best_buy[0] if isinstance(best_buy, list) and best_buy else {}
        best_sell_0 = best_sell[0] if isinstance(best_sell, list) and best_sell else {}

        bid = _normalize_price(
            raw_tick.get("best_bid_price", 0)
            or best_buy_0.get("price", 0)
        )
        ask = _normalize_price(
            raw_tick.get("best_ask_price", 0)
            or best_sell_0.get("price", 0)
        )
        bid_qty = int(
            raw_tick.get("best_bid_qty", 0)
            or best_buy_0.get("quantity", 0)
            or 0
        )
        ask_qty = int(
            raw_tick.get("best_ask_qty", 0)
            or best_sell_0.get("quantity", 0)
            or 0
        )
        volume = int(
            raw_tick.get("volume", 0)
            or raw_tick.get("vol", 0)
            or raw_tick.get("volume_trade_for_the_day", 0)
            or raw_tick.get("last_traded_quantity", 0)
            or 0
        )

        return {
            'symbol': raw_tick.get('symbol', 'UNKNOWN'),
            'token': raw_tick.get('token'),
            'seq': raw_tick.get('seq'),
            'timestamp': _normalize_ts(raw_tick.get('exchange_timestamp') or raw_tick.get('last_traded_timestamp')),
            'ltp': ltp,
            'bid': bid,
            'ask': ask,
            'volume': volume,
            'bid_qty': bid_qty,
            'ask_qty': ask_qty,
        }
    
    async def _broadcast(self, tick: dict):
        """Broadcast tick to all subscribers"""
        if not self.subscribers:
            return
            
        tasks = [subscriber(tick) for subscriber in self.subscribers]
        # Run all subscribers concurrently, ignore exceptions to prevent one sub from blocking others
        await asyncio.gather(*tasks, return_exceptions=True)
    
    def get_stats(self) -> dict:
        """Get bridge statistics"""
        return {**self.stats, 'queue_size': self.queue.qsize()}

    def get_queue_utilization(self) -> float:
        """Get queue utilization as a percentage (0.0 - 100.0). Useful for health checks."""
        if self.queue.maxsize == 0:
            return 0.0
        return (self.queue.qsize() / self.queue.maxsize) * 100.0
