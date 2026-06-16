"""
Copyright (c) 2026-present Ailrid.
Licensed under the Apache License, Version 2.0.
Project: Virid
"""

from dataclasses import dataclass
from virid.core import (
    create_virid,
    SingleMessage,
    EventMessage,
    system,
    component,
    MessageWriter,
)

# This example demonstrates the basic usage of CCS architecture
app = create_virid()


@component()
@dataclass
class Counter:
    value: int = 0


app.bind(Counter)


# Here we demonstrate three uses, namely SingleMessage that can be merged, EventMessage that cannot be merged
# And how to carry data in messages
class IncreaseMessage(SingleMessage): ...


class DecreaseMessage(EventMessage): ...


@dataclass
class SetValueMessage(SingleMessage):
    value: int


# If you don't need the content of the message
# you can directly use the messageClass parameter to specify it
@system(message_type=IncreaseMessage, priority=10)
def increment(counter: Counter) -> None:
    counter.value += 1
    MessageWriter.info(f"Increment: {counter.value}")


@system(message_type=DecreaseMessage)
def decrement(counter: Counter) -> None:
    counter.value -= 1
    MessageWriter.info(f"Decrement: {counter.value}")


# Alternatively, you can injection
@system(priority=100)
def set_value(message: SetValueMessage, counter: Counter) -> None:
    counter.value = message.value
    MessageWriter.info(f"Set Value: {counter.value}")


# Due to inheriting from SingleMessage, these two messages will be merged within a micro task queue
IncreaseMessage.send()
IncreaseMessage.send()
# Due to inheriting from EventMessage, decay will be executed twice
DecreaseMessage.send()
# Alternatively, you can directly use a Message Writer to send messages
MessageWriter.write(DecreaseMessage())
# The priority of this function is 100, so in terms of priority, setValue will be executed first
# When the constructor in the message has parameters, you can directly fill them into the. send method
SetValueMessage.send(1000)
# In the end, the order of system execution is: setValue ->increase ->decrease ->decrease
# The final count is 0->1000->1001->1000->999

app.tick()

# The final output is:
# ✔ [Virid Info] Global Info Caught:
#   Details: Set Value: 1000
#  ✔ [Virid Info] Global Info Caught:
#   Details: Increment: 1001
#  ✔ [Virid Info] Global Info Caught:
#   Details: Decrement: 1000
#  ✔ [Virid Info] Global Info Caught:
#   Details: Decrement: 999 
