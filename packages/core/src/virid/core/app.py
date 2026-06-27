"""
Copyright (c) 2026-present Ailrid.
Licensed under the Apache License, Version 2.0.
Project: Virid
"""

from __future__ import annotations
from .core import Engine
from .container import Container
from typing import Type, Callable, TypeVar, overload, Any, Protocol
from .core.message import BaseMessage, EventMessage, SingleMessage
from .core.interface import (
    SystemContext,
    TickHook,
    ExecuteHook,
    Middleware,
)
from .core.io import MessageWriter
from .decorators import component

T = TypeVar("T")
F = TypeVar("F", bound=EventMessage, contravariant=True)
H = TypeVar("H", bound=SingleMessage, contravariant=True)
O = TypeVar("O", contravariant=True)


def handle_result(res: Any) -> None:
    """统一处理返回值，支持链式反应，平铺列表投递"""
    if res is None:
        return
    # 如果返回的是列表/元组，平铺处理
    messages = res if isinstance(res, (list, tuple)) else [res]

    for m in messages:
        if isinstance(m, BaseMessage):
            MessageWriter.write(m)
        else:
            MessageWriter.warn(
                f"[virid HandleResult] Invalid Return Type: Expected BaseMessage or List[BaseMessage], got {type(m).__name__}. Ignored."
            )


class ViridPlugin(Protocol[O]):
    name: str

    def install(self, app: ViridApp, options: O) -> None: ...


@component()
class ViridApp:
    def __init__(self, max_depth: int):
        self.engine = Engine(max_depth)
        self.container = Container()
        self.installed_plugins = set()

    def on_activate(self, activate: Callable, front: bool = False) -> None:
        self.container.add_activate_hook(activate, front)

    def get(self, identifier: Type[T]) -> T:
        """Get a Controller or Component instance"""

        return self.container.get(identifier)

    def bind(self, identifier: Type[Any]):
        """Statically bind a component"""

        self.container.bind(identifier)

    def spawn(self, instance: object):
        """Dynamically bind a component"""

        self.container.spawn(instance)

    def tick(self):
        self.engine.tick()

    def register(
        self,
        func: Callable,
    ) -> Callable[[], None]:
        system_context = getattr(func, "system_context", None)
        system_config = getattr(func, "system_config", None)

        if system_context is None or system_config is None:
            raise ValueError(
                f"[Virid System] Cannot Register System: System '{func.__name__}' "
                f"must be decorated with @system before registration!"
            )

        config_params = system_config["params"]
        final_message_type = system_config["message_type"]
        priority = system_config["priority"]
        batch_mode = system_config["batch_mode"]
        message_idx = system_config["message_idx"]

        cached_components: list[Any] = [None] * len(config_params)
        is_initialized = False

        def _init_deps():
            """在系统首帧被触发时惰性求值，且只运行一次"""
            nonlocal is_initialized
            for idx, param in enumerate(config_params):
                # 如果当前槽位不是消息参数（即它是全局单例 Component 依赖项）
                if idx != message_idx:
                    inject_instance = self.get(param.annotation)
                    if inject_instance is None:
                        raise RuntimeError(
                            f"[virid System] Unknown Inject Data Types: '{param.name}' ({param.annotation.__name__}) "
                            f"is not registered in the container for system '{func.__name__}'!"
                        )
                    cached_components[idx] = inject_instance
            is_initialized = True

        # 不需要注入消息
        if message_idx is None:

            def wrapped_system(message: EventMessage | list[SingleMessage]):
                nonlocal is_initialized
                if not is_initialized:
                    _init_deps()
                handle_result(func(*cached_components))

        # 只需要注入消息
        elif len(config_params) == 1:
            if batch_mode:
                # 批处理模式：确保传入的是完整列表
                def wrapped_system(message: EventMessage | list[SingleMessage]):
                    payload = message if isinstance(message, list) else [message]
                    if __debug__:
                        if payload and not isinstance(payload[0], final_message_type):
                            raise TypeError(
                                f"[virid System] Type Mismatch: Expected list[{final_message_type.__name__}], "
                                f"got list[{type(payload[0]).__name__}]"
                            )
                    handle_result(func(payload))

            else:
                # 单例模式：切片提取最后一张最新单据
                def wrapped_system(message: EventMessage | list[SingleMessage]):
                    payload = message[-1] if isinstance(message, list) else message
                    if __debug__:
                        if not isinstance(payload, final_message_type):
                            raise TypeError(
                                f"[virid System] Type Mismatch: Expected {final_message_type.__name__}, "
                                f"got {type(payload).__name__}"
                            )
                    handle_result(func(payload))

        else:
            if batch_mode:
                # 混合模式 + 批处理
                def wrapped_system(message: EventMessage | list[SingleMessage]):
                    nonlocal is_initialized
                    if not is_initialized:
                        _init_deps()

                    payload = message if isinstance(message, list) else [message]
                    if __debug__:
                        if payload and not isinstance(payload[0], final_message_type):
                            raise TypeError(
                                f"[virid System] Type Mismatch: Expected list[{final_message_type.__name__}]"
                            )

                    call_args = cached_components[:]
                    call_args[message_idx] = payload
                    handle_result(func(*call_args))

            else:
                # 混合模式 + 单例响应
                def wrapped_system(message: EventMessage | list[SingleMessage]):
                    nonlocal is_initialized
                    if not is_initialized:
                        _init_deps()

                    payload = message[-1] if isinstance(message, list) else message
                    if __debug__:
                        if not isinstance(payload, final_message_type):
                            raise TypeError(
                                f"[virid System] Type Mismatch: Expected {final_message_type.__name__}"
                            )

                    call_args = cached_components[:]
                    call_args[message_idx] = payload
                    handle_result(func(*call_args))

        wrapped_system.system_context = SystemContext(  # type: ignore
            params=system_context["params"],
            message_type=system_context["message_type"],
            method_name=system_context["method_name"],
            original_method=system_context["original_method"],
        )

        return self.engine.register(final_message_type, wrapped_system, priority)

    def on_before_tick(self, hook: TickHook, front: bool = False):
        self.engine.on_before_tick(hook, front)

    def on_after_tick(self, hook: TickHook, front: bool = False):
        self.engine.on_after_tick(hook, front)

    @overload
    def on_before_execute(
        self,
        message_type: Type[F],
        hook: ExecuteHook[F],
        front: bool = False,
    ) -> None: ...

    @overload
    def on_before_execute(
        self,
        message_type: Type[H],
        hook: ExecuteHook[list[H]],
        front: bool = False,
    ) -> None: ...

    @overload
    def on_before_execute(
        self,
        message_type: Type[BaseMessage],
        hook: ExecuteHook[list[SingleMessage] | EventMessage],
        front: bool = False,
    ) -> None: ...

    def on_before_execute(
        self, message_type: Any, hook: Any, front: bool = False
    ) -> None:
        self.engine.on_before_execute(message_type, hook, front)

    @overload
    def on_after_execute(
        self,
        message_type: Type[F],
        hook: ExecuteHook[F],
        front: bool = False,
    ) -> None: ...

    @overload
    def on_after_execute(
        self,
        message_type: Type[H],
        hook: ExecuteHook[list[H]],
        front: bool = False,
    ) -> None: ...

    @overload
    def on_after_execute(
        self,
        message_type: Type[BaseMessage],
        hook: ExecuteHook[list[SingleMessage] | EventMessage],
        front: bool = False,
    ) -> None: ...

    def on_after_execute(
        self, message_type: Any, hook: Any, front: bool = False
    ) -> None:
        self.engine.on_after_execute(message_type, hook, front)

    def use_middleware(self, middleware: Middleware):
        self.engine.use_middleware(middleware)

    def use(self, plugin: ViridPlugin[O], options: O) -> ViridApp:
        if plugin.name in self.installed_plugins:
            MessageWriter.warn(
                f"[Virid Plugin] Duplicate Installation: Plugin {plugin.name} has already been installed."
            )
            return self

        try:
            plugin.install(self, options)
            self.installed_plugins.add(plugin.name)
        except Exception as e:
            MessageWriter.error(
                e, f"[Virid Container] Activation Hook Failed: {plugin.name}"
            )

        return self
