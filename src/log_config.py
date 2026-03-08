"""Centralized logging with loguru."""

import os
import sys

from loguru import logger

# Remove default handler and add a clear format
logger.remove()
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()
logger.add(
    sys.stderr,
    format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level=LOG_LEVEL,
)

__all__ = ["logger"]
