"""
Copyright (c) 2026-present Ailrid.
Licensed under the Apache License, Version 2.0.
Project: Virid
"""
from typing import Type, TypeVar, Any
from .message import BaseMessage, ErrorMessage, WarnMessage, InfoMessage

T = TypeVar("T", bound=BaseMessage)


publisher: Any = None


def activate_publisher(dispatcher_instance: Any):
    """供Dispatcher初始化时调用，延迟初始化"""
    global publisher
    publisher = dispatcher_instance


def publish(message: BaseMessage) -> None:
    if publisher is None:
        raise RuntimeError(
            "[Virid MessageWriter] RuntimeError: No active dispatcher found. Please ensure that a dispatcher is activated before dispatching messages."
        )
    publisher.dispatch(message)


class MessageWriter:
    """
    消息写入器。
    """

    @staticmethod
    def write(target: Type[T] | T, *args, **kwargs) -> None:
        """
        核心写入入口
        """
        if isinstance(target, type) and issubclass(target, BaseMessage):
            # 动态实例化，完美透传所有位置参数与关键字参数
            instance = target(*args, **kwargs)
        elif isinstance(target, BaseMessage):
            instance = target
        else:
            raise TypeError(
                f"[Virid MessageWriter] TypeError: Only BaseMessage subclasses or instances are allowed to be written, got: {type(target).__name__}"
            )

        # 统一收拢到惰性分发代理
        publish(instance)

    @staticmethod
    def error(error: Exception, context: str = "") -> None:
        MessageWriter.write(ErrorMessage(error=error, context=context))

    @staticmethod
    def warn(context: str) -> None:
        MessageWriter.write(WarnMessage(context=context))

    @staticmethod
    def info(context: str) -> None:
        MessageWriter.write(InfoMessage(context=context))
