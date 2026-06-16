"""
Copyright (c) 2026-present Ailrid.
Licensed under the Apache License, Version 2.0.
Project: Virid
"""
from dataclasses import dataclass
from typing import TypeVar, Callable, ParamSpec

# 定义参数规格变量和类型变量
P = ParamSpec("P")
T = TypeVar("T")


@dataclass
class BaseMessage:
    @classmethod
    def send(cls: Callable[P, T], *args: P.args, **kwargs: P.kwargs) -> None:
        # 这里的 cls 实际上就是构造函数本身
        instance = cls(*args, **kwargs)
        from .io import MessageWriter

        MessageWriter.write(instance)  # type: ignore


@dataclass
class SingleMessage(BaseMessage): ...


@dataclass
class EventMessage(BaseMessage): ...


@dataclass
class InfoMessage(EventMessage):
    context: str


@dataclass
class WarnMessage(EventMessage):
    context: str


@dataclass
class ErrorMessage(EventMessage):
    error: Exception
    context: str = ""
