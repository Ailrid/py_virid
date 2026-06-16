"""
Copyright (c) 2026-present Ailrid.
Licensed under the Apache License, Version 2.0.
Project: Virid
"""
import inspect
from functools import wraps
from typing import Any, Callable, Type, Optional, get_origin, get_args

from ..core.interface import SystemContext
from ..core.message import BaseMessage, EventMessage, SingleMessage
from ..core.io import MessageWriter
from ..app import virid_app


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


def system(
    message_type: Optional[Type[BaseMessage]] = None,
    priority: int = 0,
    singleton: bool = True,
):
    """
    系统装饰器
    :param message_type: 监听的消息类型 (可选，如果不传会自动从参数的类型注解推断)
    :param priority: 优先级，数值越大越早执行
    :param singleton: 是否为单例模式。True 传入单条消息；False 传入整个消息列表
    """

    # 提前校验 decorator 参数
    if message_type is not None and not (
        isinstance(message_type, type) and issubclass(message_type, BaseMessage)
    ):
        raise TypeError(
            f"[Virid System] TypeError: @System requires a subclass of BaseMessage, got: {message_type}"
        )

    def decorator(func: Callable) -> Callable:
        sig = inspect.signature(func)
        params = list(sig.parameters.values())

        if not params:
            raise ValueError(
                f"[Virid System] Parameter Loss: '{func.__name__}' must have at least one parameter for receiving messages!"
            )

        # 支持泛型解包的参数解析器
        msg_param_name = None
        inferred_msg_type = None

        for param in params:
            annotation = param.annotation
            if not annotation or annotation == inspect.Parameter.empty:
                continue

            target_type = None
            origin = get_origin(annotation)

            # 如果是泛型列表（如 list[DecreaseMessage] 或 List[DecreaseMessage]）
            if origin is list:
                args = get_args(annotation)
                if (
                    args
                    and isinstance(args[0], type)
                    and issubclass(args[0], BaseMessage)
                ):
                    target_type = args[0]  # 提取出里面的 DecreaseMessage 真实类型

            # 普通类型
            elif isinstance(annotation, type) and issubclass(annotation, BaseMessage):
                target_type = annotation

            # 如果找到了消息参数
            if target_type is not None:
                if msg_param_name is not None:
                    raise ValueError(
                        f"[Virid System] Multiple Messages: '{func.__name__}' cannot have multiple BaseMessage parameters."
                    )
                msg_param_name = param.name
                inferred_msg_type = target_type

        # 确定最终的消息类型 (装饰器明确指定优先 > 参数类型推断)
        final_message_type = message_type or inferred_msg_type

        if final_message_type is None:
            raise ValueError(
                f"[Virid System] Parameter Loss: Cannot infer message type for '{func.__name__}'. "
                f"Declare via @System(MyMessage) or type hint (e.g., def my_system(msg: MyMessage):)."
            )

        # 运行时警告：类型冲突
        if (
            message_type
            and inferred_msg_type
            and not issubclass(inferred_msg_type, message_type)
        ):
            MessageWriter.warn(
                f"[virid System] Type Mismatch in '{func.__name__}': Decorator expects {message_type.__name__}, "
                f"but parameter expects {inferred_msg_type.__name__}."
            )

        # 闭包缓存变量
        is_initialized = False
        cached_components: list[Any] = [None] * len(params)

        # 根据 singleton 开关，精准重组参数负载
        def build_args(message: Any) -> list:
            """构建函数入参：将消息实体和可能存在的依赖注入按顺序排好"""
            nonlocal is_initialized, cached_components

            is_incoming_list = isinstance(message, list)

            # 加工最终要塞给函数对应的参数负载
            if singleton:
                # 单例模式：函数只想要单条消息
                true_message = message[-1] if is_incoming_list else message

                # 运行时类型校验
                if not isinstance(true_message, final_message_type):
                    raise TypeError(
                        f"[virid System] Type Mismatch: Expected {final_message_type.__name__}, but received {type(true_message).__name__}"
                    )
                payload = true_message
            else:
                # 批处理模式：函数想要一个消息列表
                true_messages_list = message if is_incoming_list else [message]

                # 运行时对列表内的元素进行类型校验
                if true_messages_list and not isinstance(
                    true_messages_list[0], final_message_type
                ):
                    raise TypeError(
                        f"[virid System] Type Mismatch: Expected elements of {final_message_type.__name__}, but received {type(true_messages_list[0]).__name__}"
                    )
                payload = true_messages_list

            # 首次命中去容器捞取并缓存所有 Component 单例
            if not is_initialized:
                for idx, param in enumerate(params):
                    if param.name != msg_param_name:
                        # 只有在第一次运行时，才去全局容器里捞
                        inject_instance = virid_app.get(param.annotation)
                        if inject_instance is None:
                            raise RuntimeError(
                                f"[virid System] Unknown Inject Data Types: '{param.name}' ({param.annotation.__name__}) "
                                f"is not registered in the container for '{func.__name__}'!"
                            )
                        cached_components[idx] = inject_instance
                # 标记初始化完成
                is_initialized = True

            # 高频重组参数
            call_args = []
            for idx, param in enumerate(params):
                if param.name == msg_param_name:
                    call_args.append(payload)
                else:
                    # 直接从闭包里的数组中拿
                    call_args.append(cached_components[idx])

            return call_args

        # 包装函数 (同步)
        @wraps(func)
        def wrapped_system(message: EventMessage | list[SingleMessage]):
            # 动态组装参数
            call_args = build_args(message)
            result = func(*call_args)
            # 解析并处理返回值（支持链式反应）
            handle_result(result)
            return result

        # 给包装后的函数挂载上下文信息
        wrapped_system.system_context: SystemContext = {  # type: ignore
            "params": [p.annotation for p in params],
            "message_type": final_message_type,
            "method_name": func.__name__,
            "original_method": func,
        }

        # 自动向全局调度中心登记
        virid_app.register(final_message_type, wrapped_system, priority)

        return wrapped_system

    return decorator


def component():
    def bind_component(cls):
        cls.__virid_component__ = True
        return cls

    return bind_component
