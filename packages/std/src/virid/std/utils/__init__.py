"""
Copyright (c) 2026-present Ailrid.
Licensed under the Apache License, Version 2.0.
Project: Virid
"""

from .execute_group import activate_group_messages, execute_group, execute_block
from .nexttick import activate_next_tick, next_tick
from virid.core import ViridApp


def activate_utils(app: ViridApp):
    activate_group_messages(app)
    activate_next_tick(app)
