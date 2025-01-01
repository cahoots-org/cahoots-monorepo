"""Base logger configuration."""
import logging
import sys
import os
import structlog
from typing import Optional
from datetime import datetime

def setup_logging(log_level: str = None) -> None:
    """Configure structured logging for the application.
    
    Args:
        log_level: Optional log level override. If not provided, uses ENV_LOG_LEVEL or defaults to INFO.
    """
    # Set logging level from environment or default
    level_name = log_level or os.getenv("ENV_LOG_LEVEL", "INFO")
    level = getattr(logging, level_name, logging.INFO)
    
    # Configure standard logging
    logging.basicConfig(
        level=level,
        stream=sys.stdout,
        format="%(message)s",
    )
    
    # Configure structlog pre-chain processors
    pre_chain = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
    ]
    
    # Configure production-ready processors
    processors = [
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]
    
    # Use environment variable for environment detection
    if os.getenv("ENV", "development") == "development":
        # Development: Pretty printing
        processors.append(structlog.dev.ConsoleRenderer())
    else:
        # Production: JSON output
        processors.extend([
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer()
        ])
    
    structlog.configure(
        processors=processors,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

class BaseLogger:
    """Base structured logger wrapper."""
    
    def __init__(self, name: str):
        """Initialize logger with name.
        
        Args:
            name: Name for the logger instance
        """
        self._logger = structlog.get_logger(name)
        self.name = name
    
    def bind(self, **kwargs) -> 'BaseLogger':
        """Create a new logger with bound context data.
        
        Args:
            **kwargs: Key-value pairs to bind to the logger
        
        Returns:
            A new logger instance with bound context
        """
        new_logger = BaseLogger(self.name)
        new_logger._logger = self._logger.bind(**kwargs)
        return new_logger
    
    def _log(self, level: str, event: str, **kwargs):
        """Internal logging method.
        
        Args:
            level: Log level
            event: Event message to log
            **kwargs: Additional context to log
        """
        log_method = getattr(self._logger, level)
        log_method(
            event,
            timestamp=datetime.utcnow().isoformat(),
            service="ai_dev_team",
            **{k: v for k, v in kwargs.items() if k != 'method'}
        )
    
    def info(self, message: str, **kwargs):
        """Log info level message."""
        self._log("info", message, **kwargs)
    
    def error(self, message: str, exc_info: Optional[bool] = False, **kwargs):
        """Log error level message."""
        if exc_info:
            kwargs['exc_info'] = True
        self._log("error", message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log warning level message."""
        self._log("warning", message, **kwargs)
    
    def debug(self, message: str, **kwargs):
        """Log debug level message."""
        self._log("debug", message, **kwargs)
    
    def critical(self, message: str, **kwargs):
        """Log critical level message."""
        self._log("critical", message, **kwargs)

# Configure logging on module import with default level
setup_logging()

# Create and export default logger instance
logger = BaseLogger("app") 