"""
Copyright (c) 2026-present Ailrid.
Licensed under the Apache License, Version 2.0.
Project: Virid
"""

import time
from virid.core import (
    create_virid,
    SingleMessage,
    EventMessage,
    system,
)

# Disable logging system to ensure benchmark purity
app = create_virid(enable_logging=False)


# Define message types for benchmark
class BenchmarkMessage(SingleMessage):
    pass


class ChainRootMessage(EventMessage):
    pass


class ChainRippleMessage(SingleMessage):
    pass


# Global performance counter
performance_counter = 0


# Define systems using @system decorator
@system()
def handle_pure(message: BenchmarkMessage) -> None:
    global performance_counter
    performance_counter += 1  # Simulate minimal CPU consumption


@system()
def handle_root(message: ChainRootMessage) -> None:
    global performance_counter
    performance_counter += 1
    # Send cascading message to trigger inner while loop execution
    ChainRippleMessage.send()


@system()
def handle_ripple(message: ChainRippleMessage) -> None:
    global performance_counter
    performance_counter += 1


# Register systems
app.register(handle_pure)
app.register(handle_root)
app.register(handle_ripple)


# Metrics calculator
def report_metrics(start: float, end: float, iterations: int) -> None:
    duration_sec = end - start
    duration_ms = duration_sec * 1000
    ops_per_sec = int(iterations / duration_sec) if duration_sec > 0 else 0
    latency_us = (duration_ms / iterations) * 1000

    print(f"Duration: {duration_ms:.2f} ms")
    print(f"Throughput: {ops_per_sec:,} ops/sec")
    print(f"Latency: {latency_us:.4f} us")


# Main benchmark runner
def run_benchmark() -> None:
    global performance_counter
    iterations = 300000

    print("[Virid Core] Warming up Python interpreter...")
    # Warm up to allow interpreter or JIT optimization
    for _ in range(2000):
        BenchmarkMessage.send()
        app.tick()
        ChainRootMessage.send()
        app.tick()

    performance_counter = 0  # Reset counter

    print("\nScenario 1: Pure High-Frequency Throughput")
    start_pure = time.perf_counter()
    for _ in range(iterations):
        BenchmarkMessage.send()
        app.tick()
    end_pure = time.perf_counter()
    report_metrics(start_pure, end_pure, iterations)

    print("\nScenario 2: Cascading Message Ripple")
    start_chain = time.perf_counter()
    for _ in range(iterations):
        ChainRootMessage.send()
        app.tick()
    end_chain = time.perf_counter()
    report_metrics(start_chain, end_chain, iterations)

    print(f"\nVerification: Counter final value: {performance_counter}")


if __name__ == "__main__":
    run_benchmark()
