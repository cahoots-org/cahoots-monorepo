# src/utils/logger.py
import logging
import sys
import os

class Logger:
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        
        # Get log level from environment variable
        log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
        level = getattr(logging, log_level, logging.INFO)
        self.logger.setLevel(level)
        
        # Only add handler if root logger has no handlers
        # This prevents duplicate logging when root logger is configured
        if not logging.getLogger().handlers and not self.logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            handler.setLevel(level)
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
    
    def info(self, message: str):
        self.logger.info(message)
        
    def error(self, message: str, exc_info=False):
        self.logger.error(message, exc_info=exc_info)
        
    def warning(self, message: str):
        self.logger.warning(message)
        
    def debug(self, message: str):
        self.logger.debug(message)