import logging
import sys
from typing import Optional


def get_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """
    Create and configure a reusable project logger.

    Args:
        name: عادة __name__ ديال الملف اللي كيستعمل الlogger
        level: Logging level (default = INFO)

    Returns:
        Configured logging.Logger instance
    """

    logger = logging.getLogger(name)

    # Prevent duplicate handlers if logger already configured
    if logger.handlers:
        return logger

    logger.setLevel(level)
    logger.propagate = False  # Avoid double logging from root logger

    # ---- Console Handler ----
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)

    # ---- Format (clean + readable for agents debugging) ----
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%H:%M:%S"
    )

    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger