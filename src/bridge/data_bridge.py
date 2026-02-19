import asyncio
import logging
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
        self.stats = {
            'ticks_received': 0,
            'ticks_dropped': 0,
            'broadcast_count': 0,
        }
    
    def submit_tick(self, tick: dict):
        """
        Thread-safe tick submission from WebSocket thread.
        Non-blocking - drops tick if queue is full.
        Note: Since this is called from a thread, we use call_soon_threadsafe if loop is running,
        or just put into queue if queue is thread-safe (asyncio.Queue is NOT thread-safe for put_nowait from other threads directly safely without loop interaction usually, but here we assum integrated usage).
        
        Actually, for cross-thread submission to asyncio Queue, we need loop.call_soon_threadsafe.
        """
        try:
            loop = asyncio.get_running_loop()
            loop.call_soon_threadsafe(self.queue.put_nowait, tick)
            self.stats['ticks_received'] += 1
            if PROM_AVAILABLE:
                BRIDGE_TICKS_RECEIVED.inc()
                BRIDGE_QUEUE_SIZE.set(self.queue.qsize())
        except RuntimeError:
            # Loop might not be running or available
            logger.warning("Event loop not running, cannot submit tick")
        except QueueFull:
            self.stats['ticks_dropped'] += 1
            if PROM_AVAILABLE:
                BRIDGE_TICKS_DROPPED.inc()
            
    def subscribe(self, callback: Callable[[Dict], Awaitable[None]]):
        """Register an async callback for tick events"""
        self.subscribers.append(callback)
    
    async def start(self):
        """Start the event processing loop"""
        self.running = True
        asyncio.create_task(self._process_events())
        logger.info("DataBridge started")
    
    async def stop(self):
        """Stop the event processing loop"""
        self.running = False
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
        # Angel One specific keys to standard keys
        return {
            'symbol': raw_tick.get('symbol', 'UNKNOWN'),
            'token': raw_tick.get('token'),
            'timestamp': raw_tick.get('exchange_timestamp') or raw_tick.get('last_traded_timestamp'),
            'ltp': float(raw_tick.get('ltp', 0) or raw_tick.get('last_traded_price', 0)),
            'bid': float(raw_tick.get('best_bid_price', 0)),
            'ask': float(raw_tick.get('best_ask_price', 0)),
            'volume': int(raw_tick.get('volume', 0) or raw_tick.get('vol', 0)),
            'bid_qty': int(raw_tick.get('best_bid_qty', 0)),
            'ask_qty': int(raw_tick.get('best_ask_qty', 0)),
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
