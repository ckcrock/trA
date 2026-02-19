import sys
import os
import time
import asyncio
import pytest

# Add project root to sys.path for absolute imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.adapters.angel.rate_limiter import TokenBucketRateLimiter

def test_rate_limiter_initial_state():
    """Verify initial capacity and rate."""
    limiter = TokenBucketRateLimiter(rate=5, capacity=10)
    assert limiter.tokens == 10
    assert limiter.rate == 5

def test_rate_limiter_acquire_sync():
    """Test non-blocking sync acquisition."""
    limiter = TokenBucketRateLimiter(rate=10, capacity=10)
    
    # Acquire all tokens
    for _ in range(10):
        assert limiter.acquire(1) is True
    
    # Should fail now
    assert limiter.acquire(1) is False

def test_rate_limiter_refill():
    """Test token refill over time."""
    limiter = TokenBucketRateLimiter(rate=10, capacity=10)
    
    # Drain
    for _ in range(10):
        limiter.acquire(1)
    
    assert limiter.acquire(1) is False
    
    # Wait for 0.1s -> should get 1 token (10 tokens/sec * 0.1s = 1)
    time.sleep(0.12) # Small buffer
    assert limiter.acquire(1) is True
    assert limiter.acquire(1) is False

@pytest.mark.asyncio
async def test_rate_limiter_acquire_async():
    """Test async blocking acquisition."""
    limiter = TokenBucketRateLimiter(rate=20, capacity=2)
    
    # Use initial tokens
    assert limiter.acquire(1) is True
    assert limiter.acquire(1) is True
    
    start_time = time.time()
    # This should wait ~0.05s
    await limiter.acquire_async(1)
    end_time = time.time()
    
    assert end_time - start_time >= 0.04
    assert limiter.tokens < 1.0 # Should be nearly zero after acquisition

def test_rate_limiter_wait_and_acquire():
    """Test blocking sync acquisition."""
    limiter = TokenBucketRateLimiter(rate=20, capacity=1)
    
    limiter.acquire(1)
    
    start_time = time.time()
    limiter.wait_and_acquire(1)
    end_time = time.time()
    
    assert end_time - start_time >= 0.04
