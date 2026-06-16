"""
Copyright (c) 2026-present Ailrid.
Licensed under the Apache License, Version 2.0.
Project: Virid
"""

from virid.core import ViridApp
from .utils import activate_utils


def activate_plugin(app: ViridApp):
    activate_utils(app)


class Plugin:
    name = "std"

    # 将返回值改为 None，以契合 Protocol 的声明
    def install(self, app: ViridApp, options: None) -> None:
        activate_plugin(app)


StdPlugin = Plugin()
