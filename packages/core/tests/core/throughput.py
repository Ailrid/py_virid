"""
Copyright (c) 2026-present Ailrid.
Licensed under the Apache License, Version 2.0.
Project: Virid
"""

import time
from dataclasses import dataclass
from virid.core import (
    component,
    EventMessage,
    system,
    create_virid,
)

virid = create_virid()


@component()
@dataclass
class BenchCounter:
    value: int = 0


virid.bind(BenchCounter)

class BenchMessage(EventMessage): ...


# 用来在外部验证系统确实执行了正确次数的全局计数器
actual_run_count = 0


@system(message_type=BenchMessage)
def benchmark(counter: BenchCounter) -> None:
    global actual_run_count
    counter.value += 1
    actual_run_count += 1


if __name__ == "__main__":
    # 压测规模：跑 200,000 次完整的 [Send -> Tick -> DI -> Execute] 大循环
    TOTAL_ITERATIONS = 200_000

    print("=" * 60)
    print(" 开始 Virid 框架全链路集成压测 (Full Loop Benchmark)...")
    print(f" 压测规模: {TOTAL_ITERATIONS:,} 次 完整框架调度闭环")
    print("=" * 60)

    # 预热第一帧
    BenchMessage.send()
    virid.tick()

    # 重置计数器，开始正式全链路计时
    actual_run_count = 0
    start_time = time.perf_counter()

    # 核心吞吐量高频循环
    for _ in range(TOTAL_ITERATIONS):
        BenchMessage.send()
        virid.tick()

    end_time = time.perf_counter()

    # 性能结果统计
    elapsed_time = end_time - start_time
    throughput = TOTAL_ITERATIONS / elapsed_time

    print(f"【压测结果】")
    print(f" 完整跑完耗时 : {elapsed_time:.4f} 秒")
    print(f" 框架全链路吞吐: {throughput:,.2f} 次全循环/秒 (Ticks/sec)")
    print("-" * 60)
    print(f"【确定性状态校验】")
    print(f" 系统实际触发次数: {actual_run_count:,} 次 (预期: {TOTAL_ITERATIONS:,})")
    print("=" * 60)
