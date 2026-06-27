"""
Copyright (c) 2026-present Ailrid.
Licensed under the Apache License, Version 2.0.
Project: Virid
"""

from typing import Type
from .message import BaseMessage, SingleMessage, EventMessage
from .io import MessageWriter


class Staging:
    def __init__(self):
        # SingleMessage缓冲池
        self.signal_active: dict[Type[SingleMessage], list[SingleMessage]] = {}
        self.signal_staging: dict[Type[SingleMessage], list[SingleMessage]] = {}

        # EventMessage缓冲池
        self.event_active: list[EventMessage] = []
        self.event_staging: list[EventMessage] = []

    def stage(self, event: BaseMessage):
        """根据消息继承范式，物理隔离分流"""
        if isinstance(event, SingleMessage):
            msg_cls = type(event)
            if msg_cls not in self.signal_staging:
                self.signal_staging[msg_cls] = []
            self.signal_staging[msg_cls].append(event)

        elif isinstance(event, EventMessage):
            self.event_staging.append(event)
        else:
            MessageWriter.error(
                TypeError(
                    f"[Virid Buffer] TypeError: Message {type(event).__name__} must inherit from SingleMessage or EventMessage"
                )
            )

    def flip(self):
        """
        翻转双缓冲区：
        """
        # 物理隔离：Active 指向当前轮的快照，Staging 重置为全新容器
        self.signal_active = self.signal_staging
        self.signal_staging = {}

        self.event_active = self.event_staging
        self.event_staging = []

    def clear_signal(self) -> None:
        """
        清空指定消息类型的缓冲池
        """
        self.signal_active = {}

    def clear_event(self) -> None:
        """
        清空事件消息缓冲池
        """
        self.event_active = []

    def is_empty(self) -> bool:
        """
        判断缓冲区是否为空
        """
        return len(self.event_staging) == 0 and len(self.signal_staging) == 0

    def reset(self):
        """
        重置整个缓冲区，清空所有消息
        """
        self.signal_active = {}
        self.signal_staging = {}
        self.event_active = []
        self.event_staging = []
