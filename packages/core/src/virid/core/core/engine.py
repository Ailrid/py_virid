"""
Copyright (c) 2026-present Ailrid.
Licensed under the Apache License, Version 2.0.
Project: Virid
"""
from typing import Callable, Type
from .message import BaseMessage
from .io import MessageWriter, activate_publisher
from .registry import Registry
from .dispatcher import Dispatcher
from .interface import TickHook, ExecuteHook, Middleware


class Engine:
    def __init__(self):
        self.registry = Registry()
        self.dispatcher = Dispatcher()
        self.middlewares: list[Middleware] = []
        activate_publisher(self)

    def use_middleware(self, middleware: Middleware):
        self.middlewares.append(middleware)

    def dispatch(self, message: BaseMessage):
        """将消息放入缓冲区，等待调度器处理。"""

        # 检查消息类型
        if not isinstance(message, BaseMessage):
            MessageWriter.error(
                TypeError(
                    f"[Virid Dispatch] TypeError: Only instances of BaseMessage can be dispatched, got: {type(message).__name__}"
                )
            )

        def final_action() -> None:
            # 检查是否有对应的处理函数
            message_class = type(message)
            if message_class not in self.registry.system_task_map:
                MessageWriter.warn(
                    f"[Virid Dispatch] No System Found: No system function is registered for message: {message_class.__name__}"
                )

            self.dispatcher.mark_dirty(message)

        self.pipeline(message, final_action)

    def tick(self):
        """调度器调用，处理缓冲区中的消息。"""
        self.dispatcher.tick(self.registry.system_task_map)

    def register(
        self,
        message_class: Type[BaseMessage],
        system_fn: Callable,
        priority: int = 0,
    ):
        """注册System并返回一个无参的卸载函数。"""
        return self.registry.register(message_class, system_fn, priority)

    def pipeline(self, message: BaseMessage, final_action: Callable[[], None]):
        def next_step(idx):
            if idx < len(self.middlewares):
                self.middlewares[idx](message, lambda: next_step(idx + 1))
            else:
                final_action()

        next_step(0)

    def on_before_tick(self, hook: TickHook, front: bool = False):
        self.dispatcher.add_before_tick_hook(hook, front)

    def on_after_tick(self, hook: TickHook, front: bool = False):
        self.dispatcher.add_after_tick_hook(hook, front)

    def on_before_execute(
        self, message_type: Type[BaseMessage], hook: ExecuteHook, front: bool = False
    ):
        self.dispatcher.add_before_execute_hook(message_type, hook, front)

    def on_after_execute(
        self, message_type: Type[BaseMessage], hook: ExecuteHook, front: bool = False
    ):
        self.dispatcher.add_after_execute_hook(message_type, hook, front)
