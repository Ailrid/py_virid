"""
Copyright (c) 2026-present Ailrid.
Licensed under the Apache License, Version 2.0.
Project: Virid
"""
from typing import Type, Callable
from .message import BaseMessage
from .io import MessageWriter
from .interface import SystemTask


class Registry:
    def __init__(self):
        self.system_task_map: dict[Type[BaseMessage], list[SystemTask]] = {}

    def register(
        self,
        message_class: Type[BaseMessage],
        system_fn: Callable,
        priority: int = 0,
    ) -> Callable[[], None]:
        """
        注册系统函数并返回一个无参的卸载函数。
        """
        # 初始化消息桶
        if message_class not in self.system_task_map:
            self.system_task_map[message_class] = []

        systems = self.system_task_map[message_class]

        # 检查重复注册
        if system_fn in systems:
            func_name = getattr(system_fn, "__name__", "Anonymous")
            MessageWriter.warn(
                f"[virid Warn] System function is already registered for this message type!\n"
                f"Message Class: {message_class.__name__}\n"
                f"Function Name: {func_name}\n"
            )
            return lambda: None

        # 追加注册到桶中
        systems.append(SystemTask(system_fn=system_fn, priority=priority))

        # 返回一个闭包卸载函数
        def unregister() -> None:
            current_systems = self.system_task_map.get(message_class)
            if current_systems is not None:
                # 寻找匹配的系统索引（对标 JS 的 findIndex）
                index = next(
                    (
                        i
                        for i, s in enumerate(current_systems)
                        if s.system_fn == system_fn
                    ),
                    -1,
                )
                if index != -1:
                    current_systems.pop(index)
                    # 如果这个消息类型没有任何系统监听了，彻底删除 key，保持内存干净
                    if len(current_systems) == 0:
                        del self.system_task_map[message_class]

        return unregister
