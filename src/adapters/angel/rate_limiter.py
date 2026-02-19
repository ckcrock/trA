import time
import asyncio
from typing import Optional
from threading import Lock

class TokenBucketRateLimiter:
    """
    Thread-safe token bucket rate limiter.
    Supports both sync and async usage.
    """
    
    def __init__(self, rate: float, capacity: int = None):
        """
        Args:
            rate: Tokens per second (e.g., 3.0 for 3 req/sec)
            capacity: Bucket capacity (defaults to rate if not specified)
        """
        self.rate = rate
        self.capacity = capacity or int(rate)
        self.tokens = self.capacity
        self.last_update = time.time()
        self.lock = Lock()
    
    def _refill(self):
        """Refill tokens based on elapsed time"""
        now = time.time()
        elapsed = now - self.last_update
        tokens_to_add = elapsed * self.rate
        self.tokens = min(self.capacity, self.tokens + tokens_to_add)
        self.last_update = now
    
    def acquire(self, tokens: int = 1) -> bool:
        """
        Try to acquire tokens (non-blocking).
        Returns True if acquired, False otherwise.
        """
        with self.lock:
            self._refill()
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False
    
    async def acquire_async(self, tokens: int = 1):
        """
        Async version - waits until tokens available.
        """
        while True:
            if self.acquire(tokens):
                return
            # Wait for minimum time to get 1 token
            await asyncio.sleep(1.0 / self.rate)
    
    def wait_and_acquire(self, tokens: int = 1):
        """
        Blocking version - waits until tokens available.
        """
        while not self.acquire(tokens):
            time.sleep(1.0 / self.rate)
