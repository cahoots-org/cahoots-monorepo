"""Base logger implementation for consistent logging across the application."""
import logging
import sys
from typing import Optional
from ...config import settings

class BaseLogger:
    """Base logger class providing consistent logging functionality."""
    
    def __init__(self, name: str, level: Optional[str] = None):
        """Initialize logger with name and optional level override."""
        self.logger = logging.getLogger(name)
        self.level = level or settings.LOG_LEVEL
        self._configure_logger()
    
    def _configure_logger(self) -> None:
        """Configure logger with consistent formatting and handlers."""
        self.logger.setLevel(self.level)
        
        # Create console handler if none exists
        if not self.logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            handler.setLevel(self.level)
            
            # Create formatter
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            
            # Add handler to logger
            self.logger.addHandler(handler)
    
    def debug(self, msg: str) -> None:
        """Log debug message."""
        self.logger.debug(msg)
    
    def info(self, msg: str) -> None:
        """Log info message."""
        self.logger.info(msg)
    
    def warning(self, msg: str) -> None:
        """Log warning message."""
        self.logger.warning(msg)
    
    def error(self, msg: str) -> None:
        """Log error message."""
        self.logger.error(msg)
    
    def critical(self, msg: str) -> None:
        """Log critical message."""
        self.logger.critical(msg) 