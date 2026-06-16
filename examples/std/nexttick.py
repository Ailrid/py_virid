"""
Copyright (c) 2026-present Ailrid.
Licensed under the Apache License, Version 2.0.
Project: Virid
"""

from dataclasses import dataclass
from virid.core import (
    create_virid,
    EventMessage,
    system,
    component,
)
from virid.std import next_tick, StdPlugin

# This example demonstrates how to automatically execute some characters at the beginning of the next tick
# Enable support for Std plugin
app = create_virid().use(StdPlugin, None)


@component()
@dataclass
class Counter:
    time_A: int = 0
    time_B: int = 0
    time_C: int = 100


app.bind(Counter)


class IncreaseAMessage(EventMessage): ...


class IncreaseBMessage(EventMessage): ...


@system(message_type=IncreaseAMessage)
def increase_A(counter: Counter) -> None:
    counter.time_A += 1
    print("A :>> ", counter.time_A)


@system(message_type=IncreaseBMessage)
def increase_B(counter: Counter) -> None:
    counter.time_B += 1
    print("B :>> ", counter.time_B)


def after_tick(_context) -> None:
    print("----------After Tick----------")


def before_tick(_context) -> None:
    print("----------Before Tick----------")


app.on_after_tick(after_tick)
app.on_before_tick(before_tick)

# 触发第一帧的消息
IncreaseAMessage.send()


def _next_tick_callback() -> None:
    # These three messages must have been run after the last Tick ended
    # Therefore, if the message corresponding to Increase AMessage is synchronized,
    # then the execution has already been completed
    # If the system corresponding to Increase AMessage is asynchronous,
    # then you need an async-queue(see async-queue) to ensure order instead of NextTick
    IncreaseBMessage.send()
    IncreaseAMessage.send()
    IncreaseBMessage.send()


next_tick(_next_tick_callback)

app.tick()  # Execute the first frame (handle IncreaseAMessage, trigger the Next_tick callback at the end of the frame)
app.tick()  # Execute the second frame (processing three new messages sent in Next_tick)

# The final execution sequence should look like this
# ----------Before Tick----------
# A :>>  1
# ----------After Tick----------
# ----------Before Tick----------
# B :>>  1
# A :>>  2
# B :>>  2
# ----------After Tick----------
