"""
Copyright (c) 2026-present Ailrid.
Licensed under the Apache License, Version 2.0.
Project: Virid
"""

from dataclasses import dataclass
from typing import Callable
from virid.core import (
    create_virid,
    SingleMessage,
    EventMessage,
    system,
    component,
    ExecuteHookContext,
)
from virid.core.core.interface import TickHookContext
from virid.core.core.message import BaseMessage

# This example demonstrates how to add custom hooks
app = create_virid()


# Mark and bind this component
@component()
@dataclass
class Counter:
    value: int = 0


app.bind(Counter)


class IncreaseMessage(SingleMessage): ...


class DecreaseMessage(EventMessage): ...


class TransferMessage(SingleMessage): ...


# This hook will be executed when the component or controller is new.
# For the component, as it is a global singleton, it will only be executed once
def activation(instance):
    print("----------Activation hook triggered----------")
    print(f"Counter component activated, instance type: {instance.__class__}")

    return instance


# These two hooks will be triggered when the corresponding system is triggered after a specific message type is sent
# The first parameter is the type of the message,
# and all types inherited from the message will trigger the message
# So theoretically, if you listen to BaseMessage, all messages will trigger
# You can get a lot of information from the trigger functions of these hooks
def before_execute(
    message: list[IncreaseMessage], context: ExecuteHookContext, success: bool
):
    print("-----------Before Tick Hook Triggered-----------\n")
    # In HookContext, you can obtain the parameter types required by the current system to be executed,
    # the name of the current system, and also have a payload to pass data between hooks
    print(f"message :{message}\ncontext: {context} \nsuccess: {success}")


def after_execute(message: DecreaseMessage, context: ExecuteHookContext, success: bool):
    print("-----------After Tick Hook Triggered-----------\n")
    print(f"message :{message}\ncontext: {context} \nsuccess: {success}")
    # The information can be obtained here as above.
    # The difference is that because DecreaseMessage inherits from EventMessage,
    # the message will not be an array


# OnBeforeTick is the earliest triggered and contains a payload where data can be stored
# The stored data can be accessed in onAfterTick
# In addition, these two hooks also have a front parameter.
# When multiple hooks are registered consecutively,
# it can be determined whether the later registered hooks are inserted at the front or back of the hook queue,
# with the default being inserted at the back
def before_tick(context: TickHookContext):
    print("-----------Before Tick Hook Triggered-----------\n")
    print(f"context: {context}\n")
    context.payload["payload"] = "something"


def after_tick(context: TickHookContext):
    print("-----------After Tick Hook Triggered-----------")
    print(f"context: {context}\n")
    print(f"payload: {context.payload['payload']}\n")


def transfer(message: BaseMessage, next: Callable) -> None:
    if isinstance(message, TransferMessage):
        print("-----------transfer-----------")
        print(f"Detect TransferMessage! I will transfer it to other thread.\n")
    else:
        next()


app.on_activate(activation)
app.on_before_tick(before_tick)
app.on_after_tick(after_tick)

app.on_before_execute(IncreaseMessage, before_execute)
app.on_after_execute(DecreaseMessage, after_execute)

app.use_middleware(transfer)


@system(message_type=IncreaseMessage)
def increment(counter: Counter) -> None:
    counter.value += 1


@system(message_type=DecreaseMessage)
def decrement(counter: Counter) -> None:
    counter.value -= 1

app.register(increment)
app.register(decrement)


IncreaseMessage.send()
IncreaseMessage.send()
DecreaseMessage.send()

# Although TransferMessage appears to be executed last,
# since the message is processed in a micro queue,
# MiddleWare will intercept it first, so the output order is TransferMessage ->DeceaseMessage ->IncreaseMessage[]
# Wait, why DeceaseMessage ->Increase Message []?
# Okay, this is because by default, EventMessage will always be processed before SingleMessage
TransferMessage.send()

app.tick()

# -----------transfer-----------
# Detect TransferMessage! I will transfer it to other thread.

# -----------Before Tick Hook Triggered-----------

# context: TickHookContext(tick=0, time=1782548967.4085162, payload={})

# ----------Activation hook triggered----------
# Counter component activated, instance type: <class '__main__.Counter'>
# -----------After Tick Hook Triggered-----------

# message :DecreaseMessage()
# context: ExecuteHookContext(tick=0, context=SystemContext(params=[<class '__main__.Counter'>], message_type=<class '__main__.DecreaseMessage'>, method_name='decrement', original_method=<function decrement at 0x7fc606761440>), payload={}) 
# success: True
# -----------Before Tick Hook Triggered-----------

# message :[IncreaseMessage(), IncreaseMessage()]
# context: ExecuteHookContext(tick=0, context=SystemContext(params=[<class '__main__.Counter'>], message_type=<class '__main__.IncreaseMessage'>, method_name='increment', original_method=<function increment at 0x7fc606761300>), payload={}) 
# success: True
# -----------After Tick Hook Triggered-----------
# context: TickHookContext(tick=0, time=1782548967.4085655, payload={'payload': 'something'})

# payload: something