"""
Copyright (c) 2026-present Ailrid.
Licensed under the Apache License, Version 2.0.
Project: Virid
"""
from typing import Type, TypeVar, Callable, Any, Optional
from .core.io import MessageWriter

T = TypeVar("T")


class Container:
    def __init__(self):
        self._bindings: dict[Type[Any], tuple[Type[Any], bool]] = {}
        self._singletons: dict[Type[Any], Any] = {}

    def bind(self, identifier: Type[T], singleton: bool = False) -> None:
        """
        注册绑定。
        - to: 映射到的目标类。如果不传，默认绑定到自身（toSelf）
        - singleton: 是否为单例。默认为 False (transient)
        """
        if getattr(identifier, "__virid_component__", False) is True or getattr(identifier, "__virid_controller__", False) is True:  # type: ignore
            self._bindings[identifier] = (identifier, singleton)

        else:
            MessageWriter.error(
                TypeError(
                    f"[Virid Container] Invalid Component: The Class {identifier.__name__} whit not @Component decorator."
                )
            )

    def get(self, identifier: Type[T], on_activate: list[Callable]) -> T:
        """获取实例，执行激活流水线"""
        if identifier not in self._bindings:
            raise RuntimeError(
                f"[Virid Container] Unbound: No binding found for {identifier.__name__}"
            )

        target_ctor, is_singleton = self._bindings[identifier]

        # 如果是单例
        if is_singleton:
            if identifier not in self._singletons:
                self._singletons[identifier] = self.activate(target_ctor(), on_activate)
            return self._singletons[identifier]

        # 如果是多例
        return self.activate(target_ctor(), on_activate)

    def activate(self, component: Any, on_activate: list[Callable]):
        result = component
        for hook in on_activate:
            result = hook(result)

        return result
