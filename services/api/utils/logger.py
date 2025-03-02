"""Logging utilities for the service."""

import json
import logging
import sys
from typing import Any, Dict, Optional


class Logger:
    """Logger wrapper with structured logging support."""

    def __init__(self, name: str, level: str = "INFO"):
        """Initialize logger.

        Args:
            name: Logger name
            level: Logging level
        """
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, level.upper()))

        # Add console handler if none exists
        if not self.logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            handler.setFormatter(
                logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
            )
            self.logger.addHandler(handler)

    def _format_message(self, message: str, extra: Optional[Dict[str, Any]] = None) -> str:
        """Format log message with extra data.

        Args:
            message: Log message
            extra: Extra data to include

        Returns:
            Formatted message
        """
        if not extra:
            return message

        try:
            extra_str = json.dumps(extra)
            return f"{message} - {extra_str}"
        except Exception:
            return message

    def debug(self, message: str, extra: Optional[Dict[str, Any]] = None) -> None:
        """Log debug message.

        Args:
            message: Log message
            extra: Extra data to include
        """
        self.logger.debug(self._format_message(message, extra))

    def info(self, message: str, extra: Optional[Dict[str, Any]] = None) -> None:
        """Log info message.

        Args:
            message: Log message
            extra: Extra data to include
        """
        self.logger.info(self._format_message(message, extra))

    def warning(self, message: str, extra: Optional[Dict[str, Any]] = None) -> None:
        """Log warning message.

        Args:
            message: Log message
            extra: Extra data to include
        """
        self.logger.warning(self._format_message(message, extra))

    def error(self, message: str, extra: Optional[Dict[str, Any]] = None) -> None:
        """Log error message.

        Args:
            message: Log message
            extra: Extra data to include
        """
        self.logger.error(self._format_message(message, extra))

    def critical(self, message: str, extra: Optional[Dict[str, Any]] = None) -> None:
        """Log critical message.

        Args:
            message: Log message
            extra: Extra data to include
        """
        self.logger.critical(self._format_message(message, extra))

    def exception(
        self, message: str, exc_info: bool = True, extra: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log exception message.

        Args:
            message: Log message
            exc_info: Whether to include exception info
            extra: Extra data to include
        """
        self.logger.exception(self._format_message(message, extra), exc_info=exc_info)
