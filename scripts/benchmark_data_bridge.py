"""
Simple DataBridge performance benchmark.

Usage:
    venv\\Scripts\\python scripts\\benchmark_data_bridge.py --ticks 20000 --subscribers 2
"""

from __future__ import annotations

import argparse
import asyncio
import pathlib
import statistics
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.bridge.data_bridge import DataBridge


async def run_benchmark(ticks: int, subscribers: int, queue_size: int) -> dict:
    bridge = DataBridge(max_queue_size=queue_size)
    processed = 0
    done = asyncio.Event()
    send_times = {}
    latencies_ms = []

    async def subscriber(tick: dict):
        nonlocal processed
        seq = tick.get("seq")
        if seq in send_times:
            latency_ms = (time.perf_counter() - send_times[seq]) * 1000.0
            latencies_ms.append(latency_ms)
        processed += 1
        if processed >= ticks * subscribers:
            done.set()

    for _ in range(subscribers):
        bridge.subscribe(subscriber)

    await bridge.start()
    start = time.perf_counter()
    for i in range(ticks):
        send_times[i] = time.perf_counter()
        bridge.submit_tick(
            {
                "seq": i,
                "symbol": "SBIN-EQ",
                "token": "3045",
                "ltp": 50000 + i % 25,  # raw scaled-ish
                "best_bid_price": 49990,
                "best_ask_price": 50010,
                "last_traded_timestamp": int(time.time() * 1000),
            }
        )

    await asyncio.wait_for(done.wait(), timeout=30.0)
    end = time.perf_counter()
    await bridge.stop()

    stats = bridge.get_stats()
    elapsed = max(end - start, 1e-9)
    throughput = ticks / elapsed
    p50 = statistics.median(latencies_ms) if latencies_ms else 0.0
    p95 = sorted(latencies_ms)[int(0.95 * (len(latencies_ms) - 1))] if latencies_ms else 0.0
    return {
        "ticks_sent": ticks,
        "ticks_processed_callbacks": processed,
        "elapsed_sec": round(elapsed, 4),
        "throughput_ticks_per_sec": round(throughput, 2),
        "ticks_dropped": stats.get("ticks_dropped", 0),
        "latency_ms_p50": round(p50, 3),
        "latency_ms_p95": round(p95, 3),
        "queue_size_end": stats.get("queue_size", 0),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ticks", type=int, default=20000)
    parser.add_argument("--subscribers", type=int, default=1)
    parser.add_argument("--queue-size", type=int, default=10000)
    args = parser.parse_args()

    result = asyncio.run(
        run_benchmark(
            ticks=max(1, args.ticks),
            subscribers=max(1, args.subscribers),
            queue_size=max(100, args.queue_size),
        )
    )
    print("== DataBridge Benchmark ==")
    for k, v in result.items():
        print(f"{k}: {v}")


if __name__ == "__main__":
    main()
