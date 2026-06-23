"""
Copyright (c) 2026-present Ailrid.
Licensed under the Apache License, Version 2.0.
Project: Virid
"""

from typing import Any, Callable
from virid.core import EventMessage, ViridApp, MessageWriter, ExecuteHookContext
from contextlib import contextmanager

from virid.core.core.message import BaseMessage

# 每个 key 中缓存的执行组队列及状态映射
execute_group_map: dict[str, list[dict[str, Any]]] = {}
message_key_map: dict[int, str] = {}  # 键类型改为 int，用于存放 id(message)
key_message_map: dict[str, list[EventMessage]] = {}
call_back_map: dict[str, Callable[[bool], None]] = {}


def clear_group(group_id: str) -> None:
    for message in key_message_map[group_id]:
        message_key_map.pop(id(message), None)  # 使用 id(message) 释放
    key_message_map.pop(group_id, None)
    execute_group_map.pop(group_id, None)
    call_back_map.pop(group_id, None)


def after_execute_hook(
    message: EventMessage,
    _hook_context: ExecuteHookContext,
    success: bool,
) -> None:
    key = message_key_map.get(id(message))  # 使用 id(message) 获取
    if key:
        execute_group = execute_group_map.get(key)
        if execute_group is None:
            return

        if success:
            # 只有当前任务执行成功，才继续下一个
            if len(execute_group) > 0:
                context = execute_group.pop(0)
                resolve = context["resolve"]
                resolve()
            # 全部执行完成
            if len(execute_group) == 0:
                callback = call_back_map.get(key)
                if callback:
                    callback(True)
                clear_group(key)
        else:
            callback = call_back_map.get(key)
            if callback:
                callback(False)
            clear_group(key)
            # 如果出错了，直接取消执行队列
            MessageWriter.error(
                Exception(
                    f"[ExecuteGroup] Queue Execution Failed: Due to an error in the System execution triggered by {message.__class__.__name__}, the message group '{key}' has been cancelled"
                )
            )


def execute_group(
    messages: list[EventMessage],
    group_id: str = "default",
    callback: Callable[[bool], None] | None = None,
) -> None:
    # 修复：原代码为 id in execute_group_map，会导致判定错误
    if group_id in execute_group_map:
        MessageWriter.error(
            Exception(
                f"[ExecuteGroup] Unavailable ID: The id '{group_id}' not yet executed"
            )
        )
        if callback:
            callback(False)
        return

    # 注册这一个执行组
    execute_chain: list[dict[str, Any]] = []
    key_message_map[group_id] = messages

    for index, message in enumerate(messages):
        if index == len(messages) - 1:
            resolve = lambda: None
        else:
            # 使用默认参数绑定 next_msg，防止 Python 闭包延迟绑定导致总是拿到最后一条消息
            next_msg = messages[index + 1]
            resolve = lambda m=next_msg: MessageWriter.write(m)

        execute_chain.append({"message": message, "resolve": resolve})
        message_key_map[id(message)] = group_id  # 使用 id(message) 作为键

    if callback:
        call_back_map[group_id] = callback

    execute_group_map[group_id] = execute_chain

    # 立刻触发第一个
    MessageWriter.write(messages[0])


@contextmanager
def execute_block(
    group_id: str = "default", callback: Callable[[bool], None] | None = None
):
    #  创建一个临时篮子，用来装 with 期间产生的所有消息实例
    captured_messages: list[EventMessage] = []

    # 备份原本的全局 MessageWriter.write 方法
    original_write = MessageWriter.write

    # 定义一个拦截函数
    def mock_write(target: Any, *args, **kwargs) -> None:
        if isinstance(target, type) and issubclass(target, BaseMessage):
            # 动态实例化，完美透传所有位置参数与关键字参数
            instance = target(*args, **kwargs)
        elif isinstance(target, BaseMessage):
            instance = target
        else:
            raise TypeError(
                f"[Virid MessageWriter] TypeError: Only BaseMessage subclasses or instances are allowed to be written, got: {type(target).__name__}"
            )

        if isinstance(instance, EventMessage):
            # 如果是事件消息，拦截下来，存进篮子，先不发送
            captured_messages.append(instance)
        else:
            # 如果是其他不归群组管的消息（比如 InfoMessage 等），让它走原渠道正常发
            original_write(instance)

    # 把原本的 write 换成拦截器
    MessageWriter.write = mock_write  # type: ignore

    try:
        yield  # 此时执行 with 块内部的代码
    finally:
        # 离开 with 无论里面是否报错，雷打不动地把原本的 write 恢复回去
        # 这确保了黑魔法不会污染全局
        MessageWriter.write = original_write

    if captured_messages:
        execute_group(captured_messages, group_id=group_id, callback=callback)


def activate_group_messages(app: ViridApp) -> None:
    app.on_after_execute(EventMessage, after_execute_hook)
