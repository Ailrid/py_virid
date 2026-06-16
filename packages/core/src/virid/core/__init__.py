"""
Copyright (c) 2026-present Ailrid.
Licensed under the Apache License, Version 2.0.
Project: Virid
"""
from .app import ViridApp,ViridPlugin
from .core import *
from .decorators import *
from .util import toggle_utils


def create_virid(
    enable_logging: bool = True,
) -> ViridApp:
    from .app import virid_app

    toggle_utils(enable_logging)
    return virid_app
