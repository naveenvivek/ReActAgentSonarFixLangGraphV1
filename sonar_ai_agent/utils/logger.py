"""
Logging utilities for SonarQube AI Agent.
"""

import logging
import json
import os
import threading
from typing import Any, Dict, Optional
from datetime import datetime
from pathlib import Path


# Global file lock for thread-safe logging
_file_locks = {}
_file_locks_lock = threading.Lock()


class SonarAILogger:
    """Custom logger for SonarQube AI Agent with JSON formatting."""

    def __init__(self, config, name: str):
        """Initialize logger."""
        self.config = config
        self.name = name
        self.log_file = config.log_file
        self._is_first_entry = True

        # Get or create file lock for this log file
        with _file_locks_lock:
            if self.log_file not in _file_locks:
                _file_locks[self.log_file] = threading.Lock()
            self._file_lock = _file_locks[self.log_file]

        # Create logger
        self.logger = logging.getLogger(name)
        self.logger.setLevel(
            getattr(logging, config.log_level.upper(), logging.INFO))

        # Disable propagation to prevent duplicate logging
        self.logger.propagate = False

        # Clear any existing handlers to prevent duplicates
        self.logger.handlers.clear()

        # Initialize JSON array in log file
        self._initialize_log_file()

        # Setup handlers (always since we cleared them)
        self._setup_handlers()

    def _initialize_log_file(self):
        """Initialize the log file with JSON array opening bracket."""
        try:
            with self._file_lock:
                # Check if file exists and is empty or doesn't exist
                if not os.path.exists(self.log_file) or os.path.getsize(self.log_file) == 0:
                    with open(self.log_file, 'w', encoding='utf-8') as f:
                        f.write('[\n')
                    self._is_first_entry = True
                else:
                    # File exists, check if it needs array initialization
                    with open(self.log_file, 'r', encoding='utf-8') as f:
                        content = f.read().strip()

                    if not content:
                        # Empty file, initialize
                        with open(self.log_file, 'w', encoding='utf-8') as f:
                            f.write('[\n')
                        self._is_first_entry = True
                    elif content == '[':
                        # File has opening bracket only
                        self._is_first_entry = True
                    else:
                        # File has content, we're appending
                        self._is_first_entry = False
        except Exception:
            # If initialization fails, create new file
            try:
                with open(self.log_file, 'w', encoding='utf-8') as f:
                    f.write('[\n')
                self._is_first_entry = True
            except Exception:
                pass  # Ignore all file errors

    def _setup_handlers(self):
        """Setup console handler only (file logging is handled directly)."""
        # Console handler with simple formatter
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(console_formatter)

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
        # For JSON file logging, write directly to avoid double encoding
        log_data = {
            'timestamp': datetime.now().isoformat(),
            'level': level.upper(),
            'logger': self.name,
            'message': message,
            'module': 'logger',
            'function': '_log_with_context',
            'line': 80
        }

        # Add any additional context
        if kwargs:
            log_data.update(kwargs)

        # Write to JSON log file with proper array format (thread-safe)
        try:
            with self._file_lock:
                # Check current file state before writing
                needs_comma = False
                try:
                    if os.path.exists(self.log_file) and os.path.getsize(self.log_file) > 2:
                        with open(self.log_file, 'r', encoding='utf-8') as f:
                            content = f.read().strip()
                        # Check if we need a comma (file has entries already)
                        if content and not content.endswith('[') and not content.endswith('[\n'):
                            needs_comma = True
                except Exception:
                    needs_comma = False

                # Write the log entry
                with open(self.log_file, 'a', encoding='utf-8') as f:
                    if needs_comma:
                        f.write(',\n')
                    f.write('  ' + json.dumps(log_data, ensure_ascii=False))

        except Exception:
            pass  # Ignore file write errors

        # Also log to console with simple message
        getattr(self.logger, level)(message)

    def close_log_file(self):
        """Close the JSON array in the log file."""
        try:
            with self._file_lock:
                # Check if file needs closing bracket
                needs_closing = False
                try:
                    if os.path.exists(self.log_file):
                        with open(self.log_file, 'r', encoding='utf-8') as f:
                            content = f.read().strip()
                        # Only add closing bracket if file doesn't end with ]
                        if content and not content.endswith(']'):
                            needs_closing = True
                except Exception:
                    needs_closing = True

                if needs_closing:
                    with open(self.log_file, 'a', encoding='utf-8') as f:
                        f.write('\n]\n')
        except Exception:
            pass  # Ignore file write errors

    def get_log_file_path(self) -> str:
        """Get the absolute path to the log file."""
        return os.path.abspath(self.log_file)


def get_logger(config, name: str) -> SonarAILogger:
    """Get a logger instance."""
    return SonarAILogger(config, name)
