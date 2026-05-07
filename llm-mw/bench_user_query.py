"""
Benchmark: O(1) get_user_by_id vs O(N) load_users + loop

Measures latency improvement from the refactoring.
Run inside Docker: docker exec llm-middleware python bench_user_query.py

Expected results:
- load_users() + loop: ~2-10ms per call (scales with user count)
- get_user_by_id():    ~0.5-1ms per call (constant, indexed)
"""

import sys
import os
import time
import statistics

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.auth import load_users, get_user_by_id


def bench_load_users_loop(user_id: str, iterations: int = 100):
    """Benchmark the OLD pattern: load_users() → loop to find 1 user."""
    times = []
    for _ in range(iterations):
        start = time.perf_counter()
        users = load_users()
        result = None
        for u in users:
            if u.get("user_id") == user_id:
                result = u
                break
        elapsed = (time.perf_counter() - start) * 1000  # ms
        times.append(elapsed)
    return times


def bench_get_user_by_id(user_id: str, iterations: int = 100):
    """Benchmark the NEW pattern: get_user_by_id() direct indexed query."""
    times = []
    for _ in range(iterations):
        start = time.perf_counter()
        result = get_user_by_id(user_id)
        elapsed = (time.perf_counter() - start) * 1000  # ms
        times.append(elapsed)
    return times


def print_stats(label: str, times: list):
    """Print statistics for a benchmark run."""
    print(f"\n  {label}:")
    print(f"    Iterations : {len(times)}")
    print(f"    Mean       : {statistics.mean(times):.3f} ms")
    print(f"    Median     : {statistics.median(times):.3f} ms")
    print(f"    P95        : {sorted(times)[int(len(times) * 0.95)]:.3f} ms")
    print(f"    P99        : {sorted(times)[int(len(times) * 0.99)]:.3f} ms")
    print(f"    Min        : {min(times):.3f} ms")
    print(f"    Max        : {max(times):.3f} ms")


if __name__ == "__main__":
    ITERATIONS = 200

    users = load_users()
    user_count = len(users)
    print("=" * 60)
    print("BENCHMARK: load_users+loop vs get_user_by_id")
    print(f"Users in DB: {user_count}")
    print(f"Iterations:  {ITERATIONS}")
    print("=" * 60)

    if not users:
        print("❌ No users found. Cannot benchmark.")
        sys.exit(1)

    # Pick a user (preferably not the first one to test worst-case loop)
    test_user_id = users[-1]["user_id"] if len(users) > 1 else users[0]["user_id"]
    print(f"Target user: {test_user_id} (last in list = worst case for loop)")

    # Warmup
    print("\n🔄 Warming up...")
    _ = load_users()
    _ = get_user_by_id(test_user_id)

    # Benchmark OLD pattern
    print("\n⏱️  Benchmarking OLD pattern: load_users() + loop...")
    old_times = bench_load_users_loop(test_user_id, ITERATIONS)
    print_stats("load_users() + loop [O(N)]", old_times)

    # Benchmark NEW pattern
    print("\n⏱️  Benchmarking NEW pattern: get_user_by_id()...")
    new_times = bench_get_user_by_id(test_user_id, ITERATIONS)
    print_stats("get_user_by_id() [O(1)]", new_times)

    # Compare
    old_mean = statistics.mean(old_times)
    new_mean = statistics.mean(new_times)
    speedup = old_mean / new_mean if new_mean > 0 else float('inf')

    print("\n" + "=" * 60)
    print("📊 COMPARISON")
    print(f"  Old mean: {old_mean:.3f} ms")
    print(f"  New mean: {new_mean:.3f} ms")
    print(f"  Speedup:  {speedup:.1f}x faster")
    print()

    # Per-request impact calculation
    calls_per_request = 4  # require_user, enforce_quota, finalize, alerts
    old_per_req = old_mean * calls_per_request
    new_per_req = new_mean * calls_per_request
    saved_per_req = old_per_req - new_per_req

    print(f"  Per chat message ({calls_per_request} calls):")
    print(f"    Old: {old_per_req:.1f} ms overhead")
    print(f"    New: {new_per_req:.1f} ms overhead")
    print(f"    Saved: {saved_per_req:.1f} ms per message")
    print()

    # Projection for 200 concurrent users
    concurrent = 200
    print(f"  Projected for {concurrent} users ({concurrent} msgs/min):")
    print(f"    Old: {old_per_req * concurrent / 1000:.1f}s total overhead/min")
    print(f"    New: {new_per_req * concurrent / 1000:.1f}s total overhead/min")
    print("=" * 60)

    if speedup >= 1.5:
        print(f"✅ Refactoring provides {speedup:.1f}x improvement!")
    elif speedup >= 1.0:
        print(f"⚠️  Marginal improvement ({speedup:.1f}x). May need more users to see effect.")
    else:
        print(f"❌ Regression detected ({speedup:.1f}x). Investigate!")
