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
from .core.interface import TickHook, ExecuteHook, Middleware
from .core.io import MessageWriter

T = TypeVar("T")
F = TypeVar("F", bound=EventMessage, contravariant=True)
H = TypeVar("H", bound=SingleMessage, contravariant=True)
O = TypeVar("O", contravariant=True)

installed_plugins = set()


class ViridPlugin(Protocol[O]):
    name: str

    def install(self, app: ViridApp, options: O) -> None: ...


class ViridApp:
    def __init__(self):
        self.engine = Engine()
        self.container = Container()
        self.activate: list[Callable] = [lambda x: x]

    def on_activate(self, activate: Callable, front: bool = False) -> None:
        if front:
            self.activate.insert(0, activate)
        else:
            self.activate.append(activate)

    def get(self, identifier: Type[T]) -> T:
        return self.container.get(identifier, self.activate)

    def bind(self, identifier, singleton=True):
        self.container.bind(identifier, singleton)

    def tick(self):
        self.engine.tick()

    def register(
        self, message_class: Type[BaseMessage], system_fn: Callable, priority: int = 0
    ):
        self.engine.register(message_class, system_fn, priority)

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
        if plugin.name in installed_plugins:
            MessageWriter.warn(
                f"[Virid Plugin] Duplicate Installation: Plugin {plugin.name} has already been installed."
            )
            return self

        try:
            plugin.install(self, options)
            installed_plugins.add(plugin.name)
        except Exception as e:
            MessageWriter.error(
                e, f"[Virid Container] Activation Hook Failed: {plugin.name}"
            )

        return self


virid_app = ViridApp()


from .util import register_base_handlers

register_base_handlers(virid_app)
