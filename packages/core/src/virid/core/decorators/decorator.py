"""
Copyright (c) 2026-present Ailrid.
Licensed under the Apache License, Version 2.0.
Project: Virid
"""

import inspect

from typing import Callable, Type, Optional, get_origin, get_args
from ..core.message import BaseMessage, EventMessage, SingleMessage
from ..core.io import MessageWriter


def system(
    message_type: Optional[Type[BaseMessage]] = None,
    priority: int = 0,
):

    # 提前强校验装饰器本身的参数输入
    if message_type is not None and not (
        isinstance(message_type, type) and issubclass(message_type, BaseMessage)
    ):
        raise TypeError(
            f"[Virid System] Decorator Error: @system requires a subclass of BaseMessage, got: {type(message_type).__name__}"
        )

    def decorator(func: Callable) -> Callable:
        sig = inspect.signature(func)
        params = list(sig.parameters.values())

        if not params:
            raise ValueError(
                f"[Virid System] Parameter Loss: System '{func.__name__}' must have at least one parameter!"
            )

        msg_param_name = None
        inferred_msg_type = None
        message_idx = None
        inferred_batch_mode = None
        missing_annotation_indices = []
        batch_mode = False

        # 扫描并解析参数列表
        for idx, param in enumerate(params):
            annotation = param.annotation

            if annotation == inspect.Parameter.empty:
                missing_annotation_indices.append(idx)
                continue

            target_type = None
            current_batch_mode = False
            origin = get_origin(annotation)

            # 智能解包泛型列表提示
            if origin is list or annotation == list:
                args = get_args(annotation)
                if (
                    args
                    and isinstance(args[0], type)
                    and issubclass(args[0], BaseMessage)
                ):
                    target_type = args[0]  # 提取出 Message 类型
                    current_batch_mode = True

            # 普通单例消息提示
            elif isinstance(annotation, type) and issubclass(annotation, BaseMessage):
                target_type = annotation
                current_batch_mode = False

            if target_type is not None:
                if msg_param_name is not None:
                    raise ValueError(
                        f"[Virid System] Multiple Messages Are Not Allowed: '{func.__name__}' "
                        f"cannot declare multiple BaseMessage parameters (found '{msg_param_name}' and '{param.name}')."
                    )
                msg_param_name = param.name
                inferred_msg_type = target_type
                message_idx = idx
                inferred_batch_mode = current_batch_mode

        # 存在没有写 Type Hint 的参数
        if missing_annotation_indices:
            raise ValueError(
                f"[Virid System] Parameter Metadata Loss in '{func.__name__}': "
                f"One or more dependency parameters are missing type annotations. "
                f"This will cause DI container resolution failure. Check indices: {missing_annotation_indices}"
            )

        # 决定最终的消息类型
        final_message_type = message_type or inferred_msg_type

        if final_message_type is None:
            raise ValueError(
                f"[Virid System] System Parameter Loss: Cannot infer message type for '{func.__name__}'. "
                f"Please declare via type hint (e.g., msg: MyMessage) or options (e.g., @system(MyMessage))."
            )

        # 不允许装饰器配置和参数提示指代不同的消息实体
        if (
            message_type
            and inferred_msg_type
            and not issubclass(inferred_msg_type, message_type)
        ):
            raise ValueError(
                f"[Virid System] Multiple Messages Conflict: Cannot specify message_type={message_type.__name__} "
                f"in decorator options while method parameter signature already dictates {inferred_msg_type.__name__}."
            )

        # 决定最终的批处理模式状态
        if inferred_batch_mode is not None:
            final_batch_mode = inferred_batch_mode
            # 如果用户的显式配置跟参数类型提示产生了相悖的冲突，给予运行时警告并以更准确的类型提示为主
            if batch_mode is not None and batch_mode != inferred_batch_mode:
                MessageWriter.warn(
                    f"[virid System] Batch Mode Mismatch in '{func.__name__}': Options specified "
                    f"batch_mode={batch_mode}, but signature type hint implies batch_mode={inferred_batch_mode}. "
                    f"Overriding to match type hint."
                )
        else:
            # 允许系统完全不接收消息参数（只注入全局 Component），此时读取装饰器的选项，未指定则默认为 False
            final_batch_mode = batch_mode if batch_mode is not None else False

        # 如果是批处理模式，消息容器必须继承自 SingleMessage
        if final_batch_mode and not issubclass(final_message_type, SingleMessage):
            raise TypeError(
                f"[Virid System] Architecture Violation in '{func.__name__}': Batch processing mode (batch_mode=True) "
                f"is strictly restricted to SingleMessage subclasses. '{final_message_type.__name__}' cannot be batched."
            )

        # 如果是 EventMessage，不允许强行进入批处理逻辑
        if issubclass(final_message_type, EventMessage) and final_batch_mode:
            raise TypeError(
                f"[Virid System] Architecture Violation in '{func.__name__}': '{final_message_type.__name__}' "
                f"inherits from EventMessage and must be processed sequentially as singletons."
            )

        # 打包并统一挂载元数据
        system_context = {
            "params": [p.annotation for p in params],
            "message_type": final_message_type,
            "method_name": func.__name__,
            "original_method": func,
        }

        system_config = {
            "params": params,
            "message_type": final_message_type,
            "message_idx": message_idx,  # 如果函数没声明消息入参，则为 None
            "priority": priority,
            "batch_mode": final_batch_mode,
        }

        func.system_context = system_context  # type: ignore
        func.system_config = system_config  # type: ignore

        return func

    return decorator


def component():
    """Decorator for component"""

    def bind_component(cls):
        cls.__virid_component__ = True
        return cls

    return bind_component


def controller():
    """Decorator for controller"""

    def bind_controller(cls):
        cls.__virid_controller__ = True
        return cls

    return bind_controller
