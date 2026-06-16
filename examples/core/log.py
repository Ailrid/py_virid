"""
Copyright (c) 2026-present Ailrid.
Licensed under the Apache License, Version 2.0.
Project: Virid
"""

from dataclasses import dataclass
from virid.core import (
    create_virid,
    SingleMessage,
    ErrorMessage,
    InfoMessage,
    WarnMessage,
    system,
    component,
    MessageWriter,
)

# This example demonstrates how to replace the default logging system with a custom logging system
# The embedded logging system can be turned off in the settings
app = create_virid(enable_logging=False)


@component()
@dataclass
class Counter:
    value: int = 0


app.bind(Counter)


class TestMessage(SingleMessage): ...


@system()
def info(message: InfoMessage) -> None:
    print(f"Info: {message.context}")


@system()
def warn(message: WarnMessage) -> None:
    print(f"Warn: {message.context}")


@system()
def error(message: ErrorMessage) -> None:
    print(f"Error: {message.error}")
    print(f"Error: {message.context}")


@system()
def test(message: TestMessage) -> None:
    # If any error occurs in a system
    # it will be captured by the scheduler and automatically converted into a new Error Message
    raise Exception("Test")


MessageWriter.info("This is a info message")
MessageWriter.warn("This is a warn message")
MessageWriter.error(Exception("Error Text"), "This is a error message")

TestMessage.send()

app.tick()

# The final output is:
# Info: This is a info message
# Warn: This is a warn message
# Error: Error Text
# Error: This is a error message
# Error: Test
# Error: [virid Dispatcher]: System Error. 
# SystemLocation: test 
# MessageName: list 
# MessageData: [TestMessage()] 

