"""
Copyright (c) 2026-present Ailrid.
Licensed under the Apache License, Version 2.0.
Project: Virid
"""

from typing import Callable, Any
from virid.core import ViridApp

# 一个简单的 nextTick 任务队列
tick_task_queue: list[Callable[[], None]] = []


def after_tick_hook(context: Any) -> None:
    global tick_task_queue
    if len(tick_task_queue) == 0:
        return

    # 严格遵循你 TS 原版的双缓冲/清空逻辑
    for task in tick_task_queue:
        task()
    tick_task_queue = []


def next_tick(task: Callable[[], None]) -> None:
    tick_task_queue.append(task)


def activate_next_tick(app: ViridApp) -> None:
    app.on_after_tick(after_tick_hook)
