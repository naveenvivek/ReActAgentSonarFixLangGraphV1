"""
Logging utilities for SonarQube AI Agent.
"""

import logging
import json
import os
from typing import Any, Dict, Optional
from datetime import datetime
from pathlib import Path


class SonarAILogger:
    """Custom logger for SonarQube AI Agent with JSON formatting."""

    def __init__(self, config, name: str):
        """Initialize logger."""
        self.config = config
        self.name = name
        self.log_file = config.log_file

        # Create logger
        self.logger = logging.getLogger(name)
        self.logger.setLevel(
            getattr(logging, config.log_level.upper(), logging.INFO))

        # Avoid duplicate handlers
        if not self.logger.handlers:
            self._setup_handlers()

    def _setup_handlers(self):
        """Setup file and console handlers."""
        # File handler with JSON formatter
        file_handler = logging.FileHandler(self.log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_formatter = JSONFormatter()
        file_handler.setFormatter(file_formatter)

        # Console handler with simple formatter
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(console_formatter)

        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)

    def info(self, message: str, **kwargs):
        """Log info message with optional structured data."""
        self._log_with_context('info', message, **kwargs)

    def warning(self, message: str, **kwargs):
        """Log warning message with optional structured data."""
        self._log_with_context('warning', message, **kwargs)

    def error(self, message: str, **kwargs):
        """Log error message with optional structured data."""
        self._log_with_context('error', message, **kwargs)

    def debug(self, message: str, **kwargs):
        """Log debug message with optional structured data."""
        self._log_with_context('debug', message, **kwargs)

    def _log_with_context(self, level: str, message: str, **kwargs):
        """Log message with structured context."""
        log_data = {
            'message': message,
            'level': level.upper(),
            'timestamp': datetime.now().isoformat(),
            'logger_name': self.name
        }

        # Add any additional context
        if kwargs:
            log_data.update(kwargs)

        # Use appropriate logging level
        getattr(self.logger, level)(json.dumps(log_data, ensure_ascii=False))

        # Add line spacing after each log entry for better readability
        if hasattr(self.logger.handlers[0], 'stream'):
            try:
                with open(self.log_file, 'a', encoding='utf-8') as f:
                    f.write('\n')
            except Exception:
                pass  # Ignore file write errors for line spacing

    def get_log_file_path(self) -> str:
        """Get the absolute path to the log file."""
        return os.path.abspath(self.log_file)


class JSONFormatter(logging.Formatter):
    """JSON formatter for log records."""

    def format(self, record):
        """Format log record as JSON."""
        log_data = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }

        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)

        return json.dumps(log_data, ensure_ascii=False)


def get_logger(config, name: str) -> SonarAILogger:
    """Get a logger instance."""
    return SonarAILogger(config, name)
