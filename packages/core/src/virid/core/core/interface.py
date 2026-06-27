"""
Copyright (c) 2026-present Ailrid.
Licensed under the Apache License, Version 2.0.
Project: Virid
"""

from dataclasses import dataclass
from typing import Any, Callable, TypeVar
from .message import BaseMessage

T = TypeVar("T")


@dataclass
class SystemContext:
    """
    系统上下文，包含系统执行时的相关信息
    """

    params: list[Any]
    message_type: type[BaseMessage]
    method_name: str
    original_method: Callable

@dataclass
class SystemTask:
    """
    系统任务，包含系统函数和相关信息
    """

    system_fn: Callable
    priority: int


@dataclass
class TickHookContext:
    """
    TickHook 上下文，包含 tickHook 的相关信息
    """

    tick: int
    time: float
    payload: dict[str, Any]


@dataclass
class ExecuteHookContext:
    """
    ExecuteHook 上下文，包含 executeHook 的相关信息
    """

    tick: int
    context: SystemContext
    payload: dict[str, Any]


ExecuteHook = Callable[[T, ExecuteHookContext, bool], None]

TickHook = Callable[[TickHookContext], None]

Middleware = Callable[[BaseMessage, Callable[[], None]], None]
