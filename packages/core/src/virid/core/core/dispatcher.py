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
from .staging import Staging


class ExecutionTask:

    def __init__(
        self,
        system_fn: Callable,
        message: EventMessage | list[SingleMessage],
        priority: int,
        hook_context: ExecuteHookContext,
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
        self.message = message
        self.system_fn = system_fn
        self.priority = priority
        self.hook_context = hook_context
        self.before_execute_hooks = before_execute_hooks
        self.after_execute_hooks = after_execute_hooks
        self.success = True

    def trigger_hook(
        self,
        hooks: list[
            tuple[
                type[BaseMessage],
                ExecuteHook,
            ]
        ],
    ):
        message = self.message[0] if isinstance(self.message, list) else self.message
        try:
            for hook in hooks:
                if isinstance(message, hook[0]):
                    hook[1](self.message, self.hook_context, self.success)
        except Exception as e:
            MessageWriter.error(e, f"[Virid Hook] System Execute Hook Error.\n")

    def execute(
        self,
    ):
        success = True
        self.trigger_hook(self.before_execute_hooks)
        try:
            self.system_fn(self.message)
        except Exception as e:
            success = False
            self.trigger_hook(self.after_execute_hooks)
            # 重新丢出错误
            raise e

        self.trigger_hook(self.after_execute_hooks)


class Dispatcher:
    def __init__(self, max_depth):
        self.max_depth = max_depth
        self.staging = Staging()

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

    def stage(self, message: BaseMessage):
        self.staging.stage(message)

    def tick(self, system_task_map: dict[Type[BaseMessage], list[SystemTask]]):
        # 如果已经在运行，或者没有消息，直接返回
        if self.is_running or self.staging.is_empty():
            return

        self.is_running = True

        # 只在最外层触发 before_tick_hooks
        if self.internal_depth == 0:
            self.tick_payload = {}
            self.execute_hooks(self.before_tick_hooks)

        try:
            # 用 while 循环代替递归，消化这一个 tick 衍生出的所有消息
            while not self.staging.is_empty():
                
                if self.internal_depth > self.max_depth:
                    self.staging.reset()
                    print(
                        f"[Virid Dispatcher] Internal depth exceeded {self.max_depth}. Possible infinite loop detected. The dispatcher will stop processing this tick."
                    )
                    break  # 超过强制中断循环

                self.internal_depth += 1
                try:
                    self.staging.flip()
                    tasks = self.collect_tasks(system_task_map)
                    self.execute_tasks(tasks)
                except Exception as e:
                    MessageWriter.error(e)
        finally:
            self.is_running = False
            self.internal_depth = 0
            self.execute_hooks(self.after_tick_hooks)
            self.tick_counter += 1

    def collect_tasks(
        self,
        system_task_map: dict[Type[BaseMessage], list[SystemTask]],
    ):
        tasks: list[ExecutionTask] = []
        # 处理Event消息
        for msg in self.staging.event_active:
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
                        self.before_execute_hooks,
                        self.after_execute_hooks,
                    )
                )

        # 处理Signal消息
        for msg_cls, msg_list in self.staging.signal_active.items():
            for system_task in system_task_map.get(msg_cls, []):
                tasks.append(
                    ExecutionTask(
                        system_task.system_fn,
                        msg_list,
                        system_task.priority,
                        ExecuteHookContext(
                            tick=self.tick_counter,
                            context=system_task.system_fn.system_context,  # type: ignore
                            payload={},
                        ),
                        self.before_execute_hooks,
                        self.after_execute_hooks,
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
                task.execute()
            except Exception as e:
                MessageWriter.error(
                    e,
                    f"[virid Dispatcher]: System Error. \n"
                    + f"SystemName: {task.system_fn.system_context['method_name']} \n"  # type: ignore
                    + f"MessageName: {type(task.message).__name__} \n"
                    + f"MessageData: {task.message} \n",
                )

    def execute_hooks(self, tick_hooks: list[TickHook]):
        hooks_context = TickHookContext(
            tick=self.tick_counter, time=time.time(), payload=self.tick_payload
        )
        try:
            for hook in tick_hooks:
                hook(hooks_context)
        except Exception as e:
            MessageWriter.error(e, f"[Virid Dispatcher]: Tick Hook Error.\n")
