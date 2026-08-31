"""
Miscellaneous utility functions for the VIL system.

This module contains helper functions used throughout the VIL codebase.
Currently it provides simple wrappers for configuring logging.
"""

import logging
from typing import Optional


def configure_logging(level: int = logging.INFO, fmt: Optional[str] = None) -> None:
    """Configure the root logger with a sensible default format.

    Parameters
    ----------
    level : int, optional
        Logging level.  Defaults to `logging.INFO`.
    fmt : str, optional
        Logging format string.  If omitted, a default format is used.
    """
    fmt = fmt or "[%(levelname)s] %(asctime)s - %(name)s: %(message)s"
    logging.basicConfig(level=level, format=fmt)