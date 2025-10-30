"""Structured logging for Auto-TDD system."""
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from config import Config

class StructuredLogger:
    """JSON-based structured logger with console and file output."""
    
    def __init__(self, name: str, log_file: str = None):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, Config.LOG_LEVEL))
        
        # Console handler with UTF-8 encoding for Windows
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(console_formatter)
        
        # Force UTF-8 encoding on Windows to handle emojis
        if hasattr(sys.stdout, 'reconfigure'):
            try:
                sys.stdout.reconfigure(encoding='utf-8')
            except:
                pass  # If reconfigure fails, continue anyway
        
        self.logger.addHandler(console_handler)
        
        # File handler with JSON
        if log_file:
            Config.ensure_directories()
            file_path = Config.LOGS_DIR / log_file
            file_handler = logging.FileHandler(file_path)
            file_handler.setLevel(logging.DEBUG)
            self.logger.addHandler(file_handler)
    
    def _log_structured(self, level: str, message: str, **kwargs):
        """Log structured data as JSON."""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": level,
            "message": message,
            **kwargs
        }
        
        if Config.LOG_FORMAT == "json":
            self.logger.log(
                getattr(logging, level),
                json.dumps(log_entry)
            )
        else:
            self.logger.log(
                getattr(logging, level),
                f"{message} {json.dumps(kwargs)}"
            )
    
    def info(self, message: str, **kwargs):
        """Log info level message."""
        self._log_structured("INFO", message, **kwargs)
    
    def debug(self, message: str, **kwargs):
        """Log debug level message."""
        self._log_structured("DEBUG", message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log warning level message."""
        self._log_structured("WARNING", message, **kwargs)
    
    def error(self, message: str, **kwargs):
        """Log error level message."""
        self._log_structured("ERROR", message, **kwargs)
    
    def critical(self, message: str, **kwargs):
        """Log critical level message."""
        self._log_structured("CRITICAL", message, **kwargs)

# Global logger instance
logger = StructuredLogger("auto_tdd", "auto_tdd.log")
