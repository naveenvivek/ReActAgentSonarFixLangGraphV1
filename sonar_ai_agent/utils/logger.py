"""
Logging utility for SonarQube AI Agent system.
Provides structured file-based logging with rotation.
"""

import logging
import logging.handlers
import os
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
from ..config import Config


class SonarAILogger:
    """Custom logger for SonarQube AI Agent with file-based logging."""
    
    def __init__(self, config: Config, name: str = "sonar_ai_agent"):
        """Initialize logger with file-based configuration."""
        self.config = config
        self.name = name
        
        # Create logs directory if it doesn't exist
        log_path = Path(config.log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Setup logger
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, config.log_level.upper()))
        
        # Remove existing handlers to avoid duplicates
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)
        
        # Setup file handler with rotation
        file_handler = logging.handlers.RotatingFileHandler(
            config.log_file,
            maxBytes=config.log_max_size,
            backupCount=config.log_backup_count
        )
        
        # Setup console handler with UTF-8 encoding
        console_handler = logging.StreamHandler()
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        # Add handlers
        self.logger.addHandler(file_handler)
        # Only add console handler if not in Windows or if UTF-8 is supported
        try:
            console_handler.stream.reconfigure(encoding='utf-8')
            self.logger.addHandler(console_handler)
        except (AttributeError, UnicodeError):
            # Skip console handler on Windows with encoding issues
            pass
        
        # Prevent propagation to root logger
        self.logger.propagate = False
    
    def info(self, message: str, **kwargs):
        """Log info message with optional metadata."""
        self._log_with_metadata(logging.INFO, message, **kwargs)
    
    def debug(self, message: str, **kwargs):
        """Log debug message with optional metadata."""
        self._log_with_metadata(logging.DEBUG, message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log warning message with optional metadata."""
        self._log_with_metadata(logging.WARNING, message, **kwargs)
    
    def error(self, message: str, **kwargs):
        """Log error message with optional metadata."""
        self._log_with_metadata(logging.ERROR, message, **kwargs)
    
    def critical(self, message: str, **kwargs):
        """Log critical message with optional metadata."""
        self._log_with_metadata(logging.CRITICAL, message, **kwargs)
    
    def _log_with_metadata(self, level: int, message: str, **kwargs):
        """Log message with structured metadata."""
        # Remove emojis for Windows compatibility
        clean_message = self._clean_message_for_windows(message)
        
        if kwargs:
            # Add metadata as JSON string
            metadata = json.dumps(kwargs, default=str, indent=None)
            full_message = f"{clean_message} | Metadata: {metadata}"
        else:
            full_message = clean_message
        
        self.logger.log(level, full_message)
    
    def _clean_message_for_windows(self, message: str) -> str:
        """Remove emojis and special characters for Windows console compatibility."""
        # Replace common emojis with text equivalents
        emoji_replacements = {
            '🚀': '[START]',
            '✅': '[SUCCESS]',
            '❌': '[ERROR]',
            '📁': '[FOLDER]',
            '🔗': '[CONNECT]',
            '📊': '[DATA]',
            'ℹ️': '[INFO]',
            '🏁': '[FINISH]',
            '🔄': '[PROCESS]',
            '🤖': '[AI]',
            '📋': '[LIST]',
            '💡': '[IDEA]',
            '🔧': '[FIX]',
            '⚠️': '[WARNING]',
            '🎯': '[TARGET]',
            '⚡': '[EFFORT]',
            '🔍': '[SEARCH]'
        }
        
        clean_message = message
        for emoji, replacement in emoji_replacements.items():
            clean_message = clean_message.replace(emoji, replacement)
        
        return clean_message
    
    def log_workflow_step(self, step_name: str, status: str, **metadata):
        """Log workflow step with structured data."""
        self.info(
            f"Workflow Step: {step_name}",
            step=step_name,
            status=status,
            timestamp=datetime.now().isoformat(),
            **metadata
        )
    
    def log_issue_analysis(self, issue_key: str, confidence: float, **metadata):
        """Log issue analysis results."""
        self.info(
            f"Issue Analysis: {issue_key}",
            issue_key=issue_key,
            confidence_score=confidence,
            analysis_timestamp=datetime.now().isoformat(),
            **metadata
        )
    
    def log_fix_plan_created(self, issue_key: str, confidence: float, effort: str, **metadata):
        """Log fix plan creation."""
        self.info(
            f"Fix Plan Created: {issue_key}",
            issue_key=issue_key,
            confidence_score=confidence,
            estimated_effort=effort,
            creation_timestamp=datetime.now().isoformat(),
            **metadata
        )
    
    def log_error_with_context(self, error: Exception, context: str, **metadata):
        """Log error with context and metadata."""
        self.error(
            f"Error in {context}: {str(error)}",
            error_type=type(error).__name__,
            error_message=str(error),
            context=context,
            error_timestamp=datetime.now().isoformat(),
            **metadata
        )
    
    def log_metrics(self, metrics_name: str, metrics_data: Dict[str, Any]):
        """Log performance metrics."""
        self.info(
            f"Metrics: {metrics_name}",
            metrics_name=metrics_name,
            metrics_data=metrics_data,
            metrics_timestamp=datetime.now().isoformat()
        )
    
    def log_session_start(self, session_id: str, **metadata):
        """Log session start."""
        self.info(
            f"Session Started: {session_id}",
            session_id=session_id,
            session_start=datetime.now().isoformat(),
            **metadata
        )
    
    def log_session_end(self, session_id: str, **metadata):
        """Log session end."""
        self.info(
            f"Session Ended: {session_id}",
            session_id=session_id,
            session_end=datetime.now().isoformat(),
            **metadata
        )


def get_logger(config: Config, name: str = "sonar_ai_agent") -> SonarAILogger:
    """Get or create a logger instance."""
    return SonarAILogger(config, name)