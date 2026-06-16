"""
Copyright (c) 2026-present Ailrid.
Licensed under the Apache License, Version 2.0.
Project: Virid
"""
from typing import Type
from .message import BaseMessage, SingleMessage, EventMessage
from .io import MessageWriter


class Stage:
    def __init__(self):
        # SingleMessage缓冲池
        self._signal_active: dict[Type[SingleMessage], list[SingleMessage]] = {}
        self._signal_staging: dict[Type[SingleMessage], list[SingleMessage]] = {}

        # EventMessage缓冲池
        self._event_active: list[EventMessage] = []
        self._event_staging: list[EventMessage] = []

    def push(self, event: BaseMessage):
        """根据消息继承范式，物理隔离分流"""
        if isinstance(event, SingleMessage):
            msg_cls = type(event)
            if msg_cls not in self._signal_staging:
                self._signal_staging[msg_cls] = []
            self._signal_staging[msg_cls].append(event)

        elif isinstance(event, EventMessage):
            self._event_staging.append(event)

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
        self._signal_active = self._signal_staging
        self._signal_staging = {}

        self._event_active = self._event_staging
        self._event_staging = []

    def peek_signal(self, msg_cls: Type[SingleMessage]) -> list[SingleMessage]:
        """
        获取指定消息类型的缓冲池中的消息
        """
        return self._signal_active.get(msg_cls, [])

    def clear_signal(self) -> None:
        """
        清空指定消息类型的缓冲池
        """
        self._signal_active.clear()

    def clear_event(self) -> None:
        """
        清空事件消息缓冲池
        """
        self._event_active.clear()

    def reset(self):
        """
        重置整个缓冲区，清空所有消息
        """
        self._signal_active = {}
        self._signal_staging = {}
        self._event_active = []
        self._event_staging = []
