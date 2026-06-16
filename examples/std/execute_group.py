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
from virid.std import execute_group, execute_block, StdPlugin

# This example demonstrates how to use message groups,
# where messages within a message group will be executed sequentially and must all succeed
app = create_virid()
app.use(StdPlugin, None)


@component()
@dataclass
class Counter:
    time_A: int = 0
    time_B: int = 0
    time_C: int = 100


app.bind(Counter)


class IncreaseAMessage(EventMessage): ...


class IncreaseBMessage(EventMessage): ...


class DecreaseMessage(EventMessage): ...


class WillErrorMessage(EventMessage): ...


@system(message_type=IncreaseAMessage)
def increase_A(counter: Counter) -> None:
    counter.time_A += 1
    print("A :>> ", counter.time_A)


@system(message_type=IncreaseBMessage)
def increase_B(counter: Counter) -> None:
    counter.time_B += 1
    print("B :>> ", counter.time_B)


@system(message_type=DecreaseMessage)
def decrease(counter: Counter) -> None:
    counter.time_C -= 1
    print("C :>> ", counter.time_C)


@system()
def will_error(message: WillErrorMessage) -> None:
    raise Exception("Error")


def print_result(success: bool) -> None:
    if success:
        print("[ExecuteGroup] Success")
    else:
        print("[ExecuteGroup] Failed")


# An execution group is a collective operation.
# Regardless of whether the system triggered by these messages is synchronous or asynchronous,
# they will execute sequentially and must not throw any errors


def main():

    with execute_block(group_id="first", callback=print_result):
        IncreaseAMessage.send()
        IncreaseBMessage.send()
        IncreaseAMessage.send()
        DecreaseMessage.send()

    app.tick()
    #  When the previous group has not been executed, first cannot be used as the key again
    #  The following group will be interrupted when executing WillError Message and will not execute Increase AMessage again

    execute_group(
        [
            IncreaseAMessage(),
            IncreaseBMessage(),
            WillErrorMessage(),
            DecreaseMessage(),
        ],
        group_id="second",
        callback=print_result,
    )
    app.tick()


main()
# A :>>  1
# B :>>  1
# A :>>  2
# C :>>  99
# [ExecuteGroup] Success
# A :>>  3
# B :>>  2
#  ✖ [Virid Error] Global Error Caught:
#   Context:
#   Details: Error: [ExecuteGroup] Queue Execution Failed: Due to an error in the System execution triggered by WillErrorMessage, the message group 'second' has been cancelled
