"""Logging utilities."""

import logging
from typing import Any, Dict, Optional


def setup_logger(
    name: str, level: int = logging.INFO, format_str: Optional[str] = None
) -> logging.Logger:
    """Set up a logger with the given name and configuration.

    Args:
        name: Logger name
        level: Logging level
        format_str: Optional format string

    Returns:
        logging.Logger: Configured logger
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setLevel(level)

        formatter = logging.Formatter(
            format_str or "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        handler.setFormatter(formatter)

        logger.addHandler(handler)

    return logger


def log_error(
    logger: logging.Logger, error: Exception, context: Optional[Dict[str, Any]] = None
) -> None:
    """Log an error with optional context.

    Args:
        logger: Logger instance
        error: Exception to log
        context: Optional context dictionary
    """
    msg = f"Error: {str(error)}"
    if context:
        msg = f"{msg} Context: {context}"
    logger.error(msg, exc_info=True)
