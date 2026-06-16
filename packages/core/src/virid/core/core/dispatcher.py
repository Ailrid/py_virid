"""
Copyright (c) 2026-present Ailrid.
Licensed under the Apache License, Version 2.0.
Project: Virid
"""

import time
from typing import Callable, Type
from .interface import (
    SystemTask,
    TickHook,
    ExecuteHook,
    TickHookContext,
    ExecuteHookContext,
)
from .io import MessageWriter
from .message import BaseMessage, SingleMessage, EventMessage
from .stage import Stage


class ExecutionTask:

    def __init__(
        self,
        system_fn: Callable,
        message: EventMessage | list[SingleMessage],
        priority: int,
        hook_context: ExecuteHookContext,
    ):
        self.message = message
        self.system_fn = system_fn
        self.priority = priority
        self.hook_context = hook_context

    def trigger_hook(
        self,
        hooks: list[
            tuple[
                type[BaseMessage],
                ExecuteHook,
            ]
        ],
        success: bool,
    ):
        # 根据是不是数组来取self.message的第一个
        message = self.message[0] if isinstance(self.message, list) else self.message
        try:
            for hook in hooks:
                if isinstance(message, hook[0]):
                    hook[1](self.message, self.hook_context, success)
        except Exception as e:
            MessageWriter.error(e, f"[Virid Hook] System Execute Hook Error.\n")

    def execute(
        self,
        before_execute_hooks: list[
            tuple[
                type[BaseMessage],
                ExecuteHook,
            ]
        ],
        after_execute_hooks: list[
            tuple[
                type[BaseMessage],
                ExecuteHook,
            ]
        ],
    ):
        success = True
        self.trigger_hook(before_execute_hooks, success)
        try:
            self.system_fn(self.message)
        except Exception as e:
            success = False
            self.trigger_hook(after_execute_hooks, success)
            # 重新丢出错误
            raise e

        self.trigger_hook(after_execute_hooks, success)


class Dispatcher:
    def __init__(self):
        self.stage = Stage()
        self.event_queue: list[EventMessage] = []
        self.dirty_signal_types: dict[Type[SingleMessage], None] = {}

        self.is_running = False
        self.internal_depth = 0
        self.tick_counter = 0

        # 两个tick hook
        self.before_tick_hooks: list[TickHook] = []
        self.after_tick_hooks: list[TickHook] = []
        self.tick_payload = {}

        # 两个execute hook
        self.before_execute_hooks: list[
            tuple[
                type[BaseMessage],
                ExecuteHook,
            ]
        ] = []
        self.after_execute_hooks: list[
            tuple[
                type[BaseMessage],
                ExecuteHook,
            ]
        ] = []

    def add_before_tick_hook(self, hook: TickHook, front: bool = False):
        if front:
            self.before_tick_hooks.insert(0, hook)
        else:
            self.before_tick_hooks.append(hook)

    def add_after_tick_hook(self, hook: TickHook, front: bool = False):
        if front:
            self.after_tick_hooks.insert(0, hook)
        else:
            self.after_tick_hooks.append(hook)

    def add_before_execute_hook(
        self, message_type: Type[BaseMessage], hook: ExecuteHook, front: bool = False
    ):
        if front:
            self.before_execute_hooks.insert(0, (message_type, hook))
        else:
            self.before_execute_hooks.append((message_type, hook))

    def add_after_execute_hook(
        self, message_type: Type[BaseMessage], hook: ExecuteHook, front: bool = False
    ):
        if front:
            self.after_execute_hooks.insert(0, (message_type, hook))
        else:
            self.after_execute_hooks.append((message_type, hook))

    def mark_dirty(self, message: BaseMessage):
        self.stage.push(message)
        # 根据消息类型放进不同的池子里
        if isinstance(message, SingleMessage):
            self.dirty_signal_types[type(message)] = None
        elif isinstance(message, EventMessage):
            self.event_queue.append(message)

    def tick(self, system_task_map: dict[Type[BaseMessage], list[SystemTask]]):

        if self.is_running or (
            len(self.dirty_signal_types) == 0 and len(self.event_queue) == 0
        ):
            return

        if self.internal_depth == 0:
            self.tick_payload = {}
            self.execute_hooks(self.before_tick_hooks)

        if self.internal_depth > 100:
            self.internal_depth = 0
            self.dirty_signal_types.clear()
            self.event_queue.clear()
            self.stage.reset()
            MessageWriter.error(
                RuntimeError(
                    "[Virid Dispatcher] Internal depth exceeded 100. Possible infinite loop detected. 💥."
                ),
            )
            return

        self.is_running = True
        self.internal_depth += 1

        # 正式开始任务
        signal_snapshot = set()
        event_snapshot = list()

        try:
            signal_snapshot, event_snapshot = self.prepare_snapshot()
            tasks = self.collect_tasks(
                event_snapshot,
                signal_snapshot,
                system_task_map,
            )
            self.execute_tasks(tasks)

        except Exception as e:
            MessageWriter.error(e)

        finally:
            self.clear()
            self.is_running = False
            if len(self.dirty_signal_types) > 0 or len(self.event_queue) > 0:
                self.tick(system_task_map)
            else:
                self.internal_depth = 0
                self.execute_hooks(self.after_tick_hooks)
                self.tick_counter += 1

    def collect_tasks(
        self,
        event_snapshot: list[EventMessage],
        signal_snapshot: list[Type[SingleMessage]],
        system_task_map: dict[Type[BaseMessage], list[SystemTask]],
    ):
        tasks: list[ExecutionTask] = []
        # 处理Event消息
        for msg in event_snapshot:
            for system_task in system_task_map.get(type(msg), []):
                tasks.append(
                    ExecutionTask(
                        system_task.system_fn,
                        msg,
                        system_task.priority,
                        ExecuteHookContext(
                            tick=self.tick_counter,
                            context=system_task.system_fn.system_context,  # type: ignore
                            payload={},
                        ),
                    )
                )

        # 处理Signal消息
        for msg_cls in signal_snapshot:
            for system_task in system_task_map.get(msg_cls, []):
                tasks.append(
                    ExecutionTask(
                        system_task.system_fn,
                        self.stage.peek_signal(msg_cls),
                        system_task.priority,
                        ExecuteHookContext(
                            tick=self.tick_counter,
                            context=system_task.system_fn.system_context,  # type: ignore
                            payload={},
                        ),
                    )
                )

        return tasks

    def execute_tasks(
        self,
        tasks: list[ExecutionTask],
    ):
        # 按照优先级排序
        tasks.sort(key=lambda task: task.priority, reverse=True)

        for task in tasks:
            try:
                task.execute(self.before_execute_hooks, self.after_execute_hooks)
            except Exception as e:
                MessageWriter.error(
                    e,
                    f"[virid Dispatcher]: System Error. \n"
                    + f"SystemLocation: {task.system_fn.__name__} \n"
                    + f"MessageName: {type(task.message).__name__} \n"
                    + f"MessageData: {task.message} \n",
                )

    def prepare_snapshot(self) -> tuple[list[type[SingleMessage]], list[EventMessage]]:
        self.stage.flip()
        signal_snapshot = list(self.dirty_signal_types.keys())
        event_snapshot = self.event_queue[:]
        self.dirty_signal_types.clear()
        self.event_queue.clear()
        return signal_snapshot, event_snapshot

    def clear(
        self,
    ):
        self.stage.clear_signal()
        self.stage.clear_event()

    def execute_hooks(self, tick_hooks: list[TickHook]):
        hooks_context = TickHookContext(
            tick=self.tick_counter, time=time.time(), payload=self.tick_payload
        )
        try:
            for hook in tick_hooks:
                hook(hooks_context)
        except Exception as e:
            MessageWriter.error(e, f"[Virid Dispatcher]: Tick Hook Error.\n")
