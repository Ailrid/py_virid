"""
Copyright (c) 2026-present Ailrid.
Licensed under the Apache License, Version 2.0.
Project: Virid
"""

from virid.core.app import ViridApp
from .core.message import ErrorMessage, InfoMessage, WarnMessage
from logging import getLogger, StreamHandler
import logging
from .decorators import system, component


class ViridFormatter(logging.Formatter):
    # 颜色与样式转义码
    RESET = "\x1b[0m"
    BOLD = "\x1b[1m"
    RED = "\x1b[31m"
    GREEN = "\x1b[32m"
    YELLOW = "\x1b[33m"
    MAGENTA = "\x1b[35m"
    CYAN = "\x1b[36m"
    GRAY = "\x1b[90m"

    def format(self, record):
        if record.levelno == logging.INFO:
            header = f"{self.GREEN}{self.BOLD} ✔ [Virid Info] {self.RESET}"
            record.msg = (
                f"{header}{self.GRAY}Global Info Caught:{self.RESET}\n"
                f"  {self.GREEN}Details:{self.RESET} {record.msg}"
            )
        elif record.levelno == logging.WARNING:
            header = f"{self.YELLOW}{self.BOLD} ⚠ [Virid Warn] {self.RESET}"
            context = f"{self.CYAN}{record.msg}{self.RESET}"
            record.msg = (
                f"{header}{self.GRAY}Global Warn Caught:{self.RESET}\n"
                f"  {self.YELLOW}Context:{self.RESET} {context}"
            )
        elif record.levelno == logging.ERROR:
            header = f"{self.RED}{self.BOLD} ✖ [Virid Error] {self.RESET}"

            if "context" in getattr(record, "msg_type", ""):
                record.msg = f"  {self.RED}Context:{self.RESET} {self.MAGENTA}{record.msg}{self.RESET}"
            else:
                record.msg = (
                    f"{header}{self.GRAY}Global Error Caught:{self.RESET}\n"
                    f"  {self.RED}Details:{self.RESET} {record.msg}"
                )

        return super().format(record)


@component()
class ViridLogger:
    def __init__(self):
        self.enable_logging = True

        # 显式使用 "virid" 作为命名空间，防止跟用户自己的 root 冲突
        self.writer = getLogger("virid")
        self.writer.setLevel(logging.INFO)

        # 切断冒泡传播
        self.writer.propagate = False

        # 专属的专用 Handler
        handler = StreamHandler()
        handler.setFormatter(ViridFormatter("%(message)s"))

        # 避免重复添加 handler（防止多次实例化 Logger 类时堆叠 handler）
        if not self.writer.handlers:
            self.writer.addHandler(handler)


@system(priority=-9999)
def error(message: ErrorMessage, logger: ViridLogger) -> None:
    if not logger.enable_logging:
        return
    logger.writer.error(message.error, extra={"msg_type": "error"})
    logger.writer.error(message.context, extra={"msg_type": "context"})


@system(priority=-9999)
def info(message: InfoMessage, logger: ViridLogger) -> None:
    if not logger.enable_logging:
        return
    logger.writer.info(message.context)


@system(priority=-9999)
def warn(message: WarnMessage, logger: ViridLogger) -> None:
    if not logger.enable_logging:
        return
    logger.writer.warning(message.context)


def register_base_handlers(virid: ViridApp) -> None:
    virid.bind(ViridLogger)
    virid.register(error)
    virid.register(info)
    virid.register(warn)
