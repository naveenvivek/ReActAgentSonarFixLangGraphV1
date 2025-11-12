"""
Logging utility for SonarQube AI Agent system.
Provides structured file-based logging with rotation.
"""

import logging
import logging.handlers
import os
import json
import sys
import traceback
import uuid
import time
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, Union, Generator
from ..config import Config


class MetadataProcessor:
    """Intelligent metadata processor for structured logging."""
    
    def __init__(self, max_depth: int = 3, max_length: int = 1000, sensitive_patterns: list = None):
        """Initialize metadata processor.
        
        Args:
            max_depth: Maximum depth for nested object processing
            max_length: Maximum length for individual values
            sensitive_patterns: List of regex patterns for sensitive data detection
        """
        self.max_depth = max_depth
        self.max_length = max_length
        self.sensitive_patterns = sensitive_patterns or [
            r'password',
            r'token',
            r'key',
            r'secret',
            r'auth',
            r'credential'
        ]
        
        # Compile regex patterns for performance
        import re
        self.compiled_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.sensitive_patterns]
    
    def process_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Process metadata with intelligent type detection and sanitization."""
        if not isinstance(metadata, dict):
            return {}
        
        processed = {}
        for key, value in metadata.items():
            processed_key = self._sanitize_key(key)
            processed_value = self._process_value(value, depth=0)
            processed[processed_key] = processed_value
        
        return processed
    
    def _process_value(self, value: Any, depth: int = 0) -> Any:
        """Process individual values with type-specific handling."""
        if depth >= self.max_depth:
            return f"<nested object at depth {depth}>"
        
        # Handle None
        if value is None:
            return None
        
        # Handle basic types
        if isinstance(value, (bool, int, float)):
            return value
        
        # Handle strings with length limits and sensitive data masking
        if isinstance(value, str):
            return self._process_string(value)
        
        # Handle lists and tuples
        if isinstance(value, (list, tuple)):
            return self._process_sequence(value, depth)
        
        # Handle dictionaries
        if isinstance(value, dict):
            return self._process_dict(value, depth)
        
        # Handle other objects
        return self._process_object(value)
    
    def _process_string(self, value: str) -> str:
        """Process string values with length limits and sensitive data masking."""
        # Check for sensitive data patterns
        for pattern in self.compiled_patterns:
            if pattern.search(value):
                return self._mask_sensitive_data(value)
        
        # Apply length limits
        if len(value) > self.max_length:
            return value[:self.max_length] + "... [truncated]"
        
        return value
    
    def _process_sequence(self, value: Union[list, tuple], depth: int) -> list:
        """Process list/tuple values with intelligent truncation."""
        if not value:
            return []
        
        # For small sequences, process all items
        if len(value) <= 5:
            return [self._process_value(item, depth + 1) for item in value]
        
        # For large sequences, show first few items and count
        processed_items = [self._process_value(item, depth + 1) for item in value[:3]]
        processed_items.append(f"... +{len(value) - 3} more items")
        return processed_items
    
    def _process_dict(self, value: dict, depth: int) -> dict:
        """Process dictionary values recursively."""
        if not value:
            return {}
        
        processed = {}
        for k, v in value.items():
            processed_key = self._sanitize_key(str(k))
            processed_value = self._process_value(v, depth + 1)
            processed[processed_key] = processed_value
        
        return processed
    
    def _process_object(self, value: Any) -> str:
        """Process other object types."""
        try:
            # Try to get a meaningful string representation
            if hasattr(value, '__dict__'):
                # For objects with attributes, show class name and key attributes
                class_name = value.__class__.__name__
                attr_count = len(value.__dict__)
                return f"<{class_name} object with {attr_count} attributes>"
            else:
                # For other objects, use string representation with length limit
                str_repr = str(value)
                if len(str_repr) > self.max_length:
                    str_repr = str_repr[:self.max_length] + "... [truncated]"
                return str_repr
        except Exception:
            return f"<{type(value).__name__} object>"
    
    def _sanitize_key(self, key: str) -> str:
        """Sanitize dictionary keys."""
        # Check if key contains sensitive patterns
        for pattern in self.compiled_patterns:
            if pattern.search(key):
                return f"{key[:3]}***"
        
        return key
    
    def _mask_sensitive_data(self, value: str) -> str:
        """Mask sensitive data in strings."""
        if len(value) <= 8:
            return "***"
        
        # Show first 3 and last 3 characters, mask the middle
        return f"{value[:3]}***{value[-3:]}"
    
    def detect_circular_references(self, obj: Any, seen: set = None) -> bool:
        """Detect circular references in nested objects."""
        if seen is None:
            seen = set()
        
        obj_id = id(obj)
        if obj_id in seen:
            return True
        
        seen.add(obj_id)
        
        if isinstance(obj, dict):
            for value in obj.values():
                if self.detect_circular_references(value, seen.copy()):
                    return True
        elif isinstance(obj, (list, tuple)):
            for item in obj:
                if self.detect_circular_references(item, seen.copy()):
                    return True
        
        return False


class StructuredFormatter(logging.Formatter):
    """Enhanced formatter for structured, human-readable log output."""
    
    def __init__(self, 
                 console_output: bool = True,
                 color_enabled: bool = True,
                 max_metadata_depth: int = 3,
                 max_metadata_length: int = 1000):
        """Initialize structured formatter.
        
        Args:
            console_output: Whether this formatter is for console output
            color_enabled: Whether to use color coding for console output
            max_metadata_depth: Maximum depth for nested metadata formatting
            max_metadata_length: Maximum length for individual metadata values
        """
        super().__init__()
        self.console_output = console_output
        self.color_enabled = color_enabled and console_output
        self.max_metadata_depth = max_metadata_depth
        self.max_metadata_length = max_metadata_length
        
        # Initialize metadata processor
        self.metadata_processor = MetadataProcessor(
            max_depth=max_metadata_depth,
            max_length=max_metadata_length
        )
        
        # Color codes for different log levels (console only)
        self.colors = {
            'DEBUG': '\033[36m',    # Cyan
            'INFO': '\033[32m',     # Green
            'WARNING': '\033[33m',  # Yellow
            'ERROR': '\033[31m',    # Red
            'CRITICAL': '\033[35m', # Magenta
            'RESET': '\033[0m'      # Reset
        } if self.color_enabled else {}
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record with structured output."""
        try:
            # Extract and process metadata from record if present
            raw_metadata = getattr(record, 'metadata', {})
            raw_performance_data = getattr(record, 'performance_data', {})
            
            # Process metadata through the intelligent processor
            processed_metadata = self.metadata_processor.process_metadata(raw_metadata)
            processed_performance_data = self.metadata_processor.process_metadata(raw_performance_data)
            
            if self.console_output:
                return self._format_console(record, processed_metadata, processed_performance_data)
            else:
                return self._format_file(record, processed_metadata, processed_performance_data)
                
        except Exception as e:
            # Fallback to basic formatting if structured formatting fails
            return f"[LOGGING ERROR] {record.getMessage()} | Error: {str(e)}"
    
    def _format_console(self, record: logging.LogRecord, metadata: Dict[str, Any], 
                       performance_data: Dict[str, Any]) -> str:
        """Format for human-readable console output."""
        # Format timestamp with milliseconds
        timestamp = datetime.fromtimestamp(record.created).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        
        # Apply color coding if enabled
        level_color = self.colors.get(record.levelname, '') if self.color_enabled else ''
        reset_color = self.colors.get('RESET', '') if self.color_enabled else ''
        
        # Format main log line
        performance_suffix = self._format_performance_suffix(performance_data)
        main_line = f"[{timestamp}] {level_color}{record.levelname}{reset_color}: {record.getMessage()}{performance_suffix}"
        
        # Special formatting for error logs
        if record.levelname in ['ERROR', 'CRITICAL'] and 'error_id' in metadata:
            error_summary = self._format_error_summary(metadata)
            if error_summary:
                main_line += f"\n{error_summary}"
        
        # Format metadata if present
        if metadata:
            # Filter out stack trace from console output for readability
            console_metadata = {k: v for k, v in metadata.items() 
                              if k not in ['stack_trace', 'stack_info']}
            if console_metadata:
                metadata_lines = self._format_metadata_hierarchical(console_metadata)
                return main_line + '\n' + metadata_lines
        
        return main_line
    
    def _format_error_summary(self, metadata: Dict[str, Any]) -> str:
        """Format a concise error summary for console output."""
        if 'stack_info' not in metadata or not metadata['stack_info']:
            return ""
        
        # Show only the most relevant stack frame (usually the last one)
        stack_info = metadata['stack_info']
        if stack_info:
            last_frame = stack_info[-1]
            return f"  ↳ at {last_frame['function']}() in {last_frame['file']}:{last_frame['line']}"
        
        return ""
    
    def _format_file(self, record: logging.LogRecord, metadata: Dict[str, Any], 
                    performance_data: Dict[str, Any]) -> str:
        """Format for machine-readable file output (JSON)."""
        log_entry = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'metadata': metadata,
            'performance_data': performance_data,
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # Add exception info if present
        if record.exc_info:
            log_entry['exception'] = {
                'type': record.exc_info[0].__name__ if record.exc_info[0] else None,
                'message': str(record.exc_info[1]) if record.exc_info[1] else None,
                'traceback': traceback.format_exception(*record.exc_info)
            }
        
        # Add error-specific information from metadata
        if 'error_id' in metadata:
            log_entry['error_correlation'] = {
                'error_id': metadata['error_id'],
                'error_type': metadata.get('error_type'),
                'context': metadata.get('context')
            }
        
        return json.dumps(log_entry, default=str, ensure_ascii=False)
    
    def _format_metadata_hierarchical(self, metadata: Dict[str, Any], indent_level: int = 1) -> str:
        """Format metadata with hierarchical tree-like structure."""
        if not metadata or indent_level > self.max_metadata_depth:
            return ""
        
        lines = []
        indent = "  " * indent_level
        
        for key, value in metadata.items():
            if isinstance(value, dict) and indent_level < self.max_metadata_depth:
                lines.append(f"{indent}└─ {key}:")
                nested_lines = self._format_metadata_hierarchical(value, indent_level + 1)
                if nested_lines:
                    lines.append(nested_lines)
            elif isinstance(value, (list, tuple)) and len(value) > 0:
                if len(value) <= 5:  # Show all items for small lists
                    formatted_list = [str(item) for item in value]
                    lines.append(f"{indent}└─ {key}: [{', '.join(formatted_list)}]")
                else:  # Truncate large lists
                    preview_items = [str(item) for item in value[:3]]
                    lines.append(f"{indent}└─ {key}: [{', '.join(preview_items)}, ... +{len(value)-3} more]")
            else:
                # Format single values with length limits
                value_str = str(value)
                if len(value_str) > self.max_metadata_length:
                    value_str = value_str[:self.max_metadata_length] + "... [truncated]"
                lines.append(f"{indent}└─ {key}: {value_str}")
        
        return '\n'.join(lines)
    
    def _format_performance_suffix(self, performance_data: Dict[str, Any]) -> str:
        """Format performance data as a suffix to the main log line."""
        if not performance_data:
            return ""
        
        parts = []
        
        # Duration formatting
        if 'duration_ms' in performance_data:
            duration = performance_data['duration_ms']
            if duration < 1000:
                parts.append(f"{duration:.0f}ms")
            else:
                parts.append(f"{duration/1000:.2f}s")
        
        # Throughput formatting
        if 'throughput_per_second' in performance_data:
            throughput = performance_data['throughput_per_second']
            parts.append(f"{throughput:.1f}/sec")
        
        # Items processed
        if 'items_processed' in performance_data:
            items = performance_data['items_processed']
            parts.append(f"{items} items")
        
        if parts:
            return f" [PERFORMANCE: {', '.join(parts)}]"
        
        return ""


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
        
        # Create structured formatters
        console_formatter = StructuredFormatter(
            console_output=True,
            color_enabled=getattr(config, 'console_color_enabled', True),
            max_metadata_depth=getattr(config, 'metadata_max_depth', 3),
            max_metadata_length=getattr(config, 'metadata_max_length', 1000)
        )
        
        file_formatter = StructuredFormatter(
            console_output=False,
            color_enabled=False,
            max_metadata_depth=getattr(config, 'metadata_max_depth', 3),
            max_metadata_length=getattr(config, 'metadata_max_length', 1000)
        )
        
        file_handler.setFormatter(file_formatter)
        console_handler.setFormatter(console_formatter)
        
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
        
        # Operation correlation tracking
        self._active_operations: Dict[str, Dict[str, Any]] = {}
        
        # Performance thresholds for automatic log level elevation
        self.performance_thresholds = {
            'slow_operation_ms': getattr(config, 'slow_operation_threshold_ms', 5000),  # 5 seconds
            'very_slow_operation_ms': getattr(config, 'very_slow_operation_threshold_ms', 10000),  # 10 seconds
            'low_throughput_threshold': getattr(config, 'low_throughput_threshold', 1.0),  # items per second
            'high_error_rate_threshold': getattr(config, 'high_error_rate_threshold', 0.1)  # 10% error rate
        }
    
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
        
        # Create log record with metadata
        record = self.logger.makeRecord(
            self.logger.name, level, "", 0, clean_message, (), None
        )
        
        # Attach metadata and performance data to the record
        if kwargs:
            # Separate performance data from regular metadata
            performance_data = {}
            metadata = {}
            
            for key, value in kwargs.items():
                if key in ['duration_ms', 'throughput_per_second', 'items_processed', 'processing_time_seconds']:
                    performance_data[key] = value
                else:
                    metadata[key] = value
            
            record.metadata = metadata
            record.performance_data = performance_data
        else:
            record.metadata = {}
            record.performance_data = {}
        
        self.logger.handle(record)
    
    def log_operation_start(self, operation: str, **metadata) -> str:
        """Log the start of an operation and return correlation ID."""
        correlation_id = str(uuid.uuid4())[:8]  # Short correlation ID
        
        start_time = time.time()
        self._active_operations[correlation_id] = {
            'operation': operation,
            'start_time': start_time,
            'metadata': metadata.copy()
        }
        
        self.info(f"Operation started: {operation}",
                 correlation_id=correlation_id,
                 operation=operation,
                 **metadata)
        
        return correlation_id
    
    def log_operation_end(self, correlation_id: str, **metadata) -> None:
        """Log the end of an operation using correlation ID."""
        if correlation_id not in self._active_operations:
            self.warning(f"Operation end logged without matching start",
                        correlation_id=correlation_id,
                        **metadata)
            return
        
        operation_data = self._active_operations.pop(correlation_id)
        end_time = time.time()
        duration_ms = (end_time - operation_data['start_time']) * 1000
        
        # Merge start metadata with end metadata, avoiding conflicts
        combined_metadata = operation_data['metadata'].copy()
        combined_metadata.update(metadata)
        
        # Remove duration_ms from combined_metadata if it exists to avoid conflicts
        combined_metadata.pop('duration_ms', None)
        
        self.info(f"Operation completed: {operation_data['operation']}",
                 correlation_id=correlation_id,
                 operation=operation_data['operation'],
                 duration_ms=duration_ms,
                 **combined_metadata)
    
    def log_performance(self, operation: str, duration: float, **metadata) -> None:
        """Log performance metrics for an operation with threshold monitoring."""
        duration_ms = duration * 1000 if duration < 10 else duration  # Auto-detect units
        
        performance_data = {
            'duration_ms': duration_ms,
            **metadata
        }
        
        # Calculate throughput if items_processed is provided
        throughput = None
        if 'items_processed' in metadata and duration > 0:
            items = metadata['items_processed']
            duration_seconds = duration_ms / 1000
            throughput = items / duration_seconds
            performance_data['throughput_per_second'] = throughput
        
        # Determine log level based on performance thresholds
        log_level = logging.INFO
        performance_status = "normal"
        
        # Check duration thresholds
        if duration_ms >= self.performance_thresholds['very_slow_operation_ms']:
            log_level = logging.ERROR
            performance_status = "very_slow"
        elif duration_ms >= self.performance_thresholds['slow_operation_ms']:
            log_level = logging.WARNING
            performance_status = "slow"
        
        # Check throughput thresholds
        if throughput is not None and throughput < self.performance_thresholds['low_throughput_threshold']:
            if log_level < logging.WARNING:
                log_level = logging.WARNING
            performance_status = f"{performance_status}_low_throughput"
        
        # Check error rate if provided
        if 'error_rate' in metadata:
            error_rate = metadata['error_rate']
            if error_rate >= self.performance_thresholds['high_error_rate_threshold']:
                log_level = logging.ERROR
                performance_status = f"{performance_status}_high_errors"
        
        performance_data['performance_status'] = performance_status
        
        # Log with appropriate level
        message = f"Performance metrics: {operation}"
        if performance_status != "normal":
            message += f" [{performance_status.upper()}]"
        
        self._log_with_metadata(log_level, message,
                              operation=operation,
                              **performance_data)
    
    def log_with_context(self, level: int, message: str, **metadata) -> None:
        """Enhanced logging with automatic context detection."""
        # Add automatic context information
        import inspect
        frame = inspect.currentframe()
        try:
            # Get caller information
            caller_frame = frame.f_back.f_back  # Skip this method and _log_with_metadata
            if caller_frame:
                metadata.setdefault('caller_module', caller_frame.f_globals.get('__name__', 'unknown'))
                metadata.setdefault('caller_function', caller_frame.f_code.co_name)
                metadata.setdefault('caller_line', caller_frame.f_lineno)
        finally:
            del frame  # Prevent reference cycles
        
        self._log_with_metadata(level, message, **metadata)
    
    @contextmanager
    def performance_context(self, operation: str, **metadata) -> Generator[Dict[str, Any], None, None]:
        """Context manager for automatic performance tracking with threshold monitoring."""
        correlation_id = self.log_operation_start(operation, **metadata)
        start_time = time.time()
        context_data = {
            'correlation_id': correlation_id, 
            'operation': operation,
            'start_time': start_time,
            'items_processed': 0,
            'errors_encountered': 0
        }
        
        try:
            yield context_data
            # Operation completed successfully
            end_time = time.time()
            duration = end_time - start_time
            duration_ms = duration * 1000
            
            # Calculate performance metrics from context
            items_processed = context_data.get('items_processed', 0)
            errors_encountered = context_data.get('errors_encountered', 0)
            
            # Calculate error rate if items were processed
            error_rate = 0.0
            if items_processed > 0:
                error_rate = errors_encountered / items_processed
            
            # Prepare performance data
            performance_data = {
                'status': 'success',
                'duration_ms': duration_ms
            }
            
            if items_processed > 0:
                performance_data['items_processed'] = items_processed
                performance_data['throughput_per_second'] = items_processed / duration
            
            if errors_encountered > 0:
                performance_data['errors_encountered'] = errors_encountered
                performance_data['error_rate'] = error_rate
            
            # Add any additional context data
            for key, value in context_data.items():
                if key not in ['correlation_id', 'operation', 'start_time', 'items_processed', 'errors_encountered']:
                    performance_data[key] = value
            
            # Log performance metrics with threshold checking
            self.log_performance(operation, duration, **performance_data)
            
            # Also log operation end
            self.log_operation_end(correlation_id, **performance_data)
            
        except Exception as e:
            # Operation failed
            end_time = time.time()
            duration = end_time - start_time
            duration_ms = duration * 1000
            
            # Calculate metrics even for failed operations
            items_processed = context_data.get('items_processed', 0)
            errors_encountered = context_data.get('errors_encountered', 0) + 1  # Add the current exception
            
            performance_data = {
                'status': 'failed',
                'duration_ms': duration_ms,
                'error_type': type(e).__name__,
                'error_message': str(e)
            }
            
            if items_processed > 0:
                performance_data['items_processed'] = items_processed
                performance_data['errors_encountered'] = errors_encountered
                performance_data['error_rate'] = errors_encountered / (items_processed + 1)
            
            self.log_operation_end(correlation_id, **performance_data)
            raise  # Re-raise the exception
    
    def log_performance_summary(self, operation: str, metrics: Dict[str, Any]) -> None:
        """Log a performance summary with aggregated metrics."""
        # Calculate derived metrics
        total_operations = metrics.get('total_operations', 0)
        total_duration = metrics.get('total_duration_ms', 0)
        successful_operations = metrics.get('successful_operations', 0)
        failed_operations = metrics.get('failed_operations', 0)
        
        summary_data = {
            'operation': operation,
            'total_operations': total_operations,
            'successful_operations': successful_operations,
            'failed_operations': failed_operations,
            'total_duration_ms': total_duration,
            **metrics
        }
        
        # Calculate derived metrics
        if total_operations > 0:
            summary_data['success_rate'] = successful_operations / total_operations
            summary_data['failure_rate'] = failed_operations / total_operations
            summary_data['average_duration_ms'] = total_duration / total_operations
        
        if total_duration > 0:
            summary_data['operations_per_second'] = (total_operations * 1000) / total_duration
        
        # Determine log level based on performance
        log_level = logging.INFO
        if summary_data.get('failure_rate', 0) >= self.performance_thresholds['high_error_rate_threshold']:
            log_level = logging.ERROR
        elif summary_data.get('average_duration_ms', 0) >= self.performance_thresholds['slow_operation_ms']:
            log_level = logging.WARNING
        
        self._log_with_metadata(log_level, f"Performance summary: {operation}", **summary_data)
    
    def create_performance_tracker(self, operation: str) -> 'PerformanceTracker':
        """Create a performance tracker for an operation."""
        return PerformanceTracker(self, operation)
    
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
        """Enhanced error logging with context, stack trace, and correlation."""
        # Generate error correlation ID
        error_id = str(uuid.uuid4())[:8]
        
        # Get stack trace information
        import traceback
        stack_trace = traceback.format_exception(type(error), error, error.__traceback__)
        
        # Extract relevant stack frame information
        stack_info = []
        for frame in traceback.extract_tb(error.__traceback__):
            stack_info.append({
                'file': frame.filename,
                'line': frame.lineno,
                'function': frame.name,
                'code': frame.line
            })
        
        # Prepare error metadata
        error_metadata = {
            'error_id': error_id,
            'error_type': type(error).__name__,
            'error_message': str(error),
            'context': context,
            'error_timestamp': datetime.now().isoformat(),
            'stack_trace': stack_trace,
            'stack_info': stack_info,
            **metadata
        }
        
        # Check for error patterns and escalation
        error_level = self._determine_error_level(error, context, metadata)
        
        self._log_with_metadata(
            error_level,
            f"Error in {context}: {str(error)} [ID: {error_id}]",
            **error_metadata
        )
        
        return error_id
    
    def log_error_recovery(self, error_id: str, recovery_action: str, success: bool, **metadata):
        """Log error recovery attempts."""
        level = logging.INFO if success else logging.WARNING
        status = "successful" if success else "failed"
        
        self._log_with_metadata(
            level,
            f"Error recovery {status}: {recovery_action}",
            error_id=error_id,
            recovery_action=recovery_action,
            recovery_success=success,
            recovery_timestamp=datetime.now().isoformat(),
            **metadata
        )
    
    def log_error_pattern(self, pattern_name: str, occurrences: int, time_window: str, **metadata):
        """Log detected error patterns."""
        self.warning(
            f"Error pattern detected: {pattern_name}",
            pattern_name=pattern_name,
            occurrences=occurrences,
            time_window=time_window,
            pattern_timestamp=datetime.now().isoformat(),
            **metadata
        )
    
    def _determine_error_level(self, error: Exception, context: str, metadata: Dict[str, Any]) -> int:
        """Determine appropriate log level based on error type and context."""
        # Critical errors that should always be ERROR level
        critical_error_types = [
            'SystemExit', 'KeyboardInterrupt', 'MemoryError', 
            'OSError', 'IOError', 'ConnectionError'
        ]
        
        # Errors that might be warnings in certain contexts
        warning_error_types = [
            'ValueError', 'TypeError', 'AttributeError'
        ]
        
        error_type = type(error).__name__
        
        # Check for critical errors
        if error_type in critical_error_types:
            return logging.CRITICAL
        
        # Check retry count - if we've retried many times, escalate
        retry_count = metadata.get('retry_count', 0)
        if retry_count >= 3:
            return logging.ERROR
        
        # Check context - some contexts are more critical
        critical_contexts = ['database', 'authentication', 'security', 'payment']
        if any(ctx in context.lower() for ctx in critical_contexts):
            return logging.ERROR
        
        # Check if this is a known recoverable error in a non-critical context
        if error_type in warning_error_types and retry_count < 2:
            return logging.WARNING
        
        # Default to ERROR for most exceptions
        return logging.ERROR
    
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


class PerformanceTracker:
    """Performance tracker for aggregating metrics over multiple operations."""
    
    def __init__(self, logger: SonarAILogger, operation: str):
        """Initialize performance tracker."""
        self.logger = logger
        self.operation = operation
        self.metrics = {
            'total_operations': 0,
            'successful_operations': 0,
            'failed_operations': 0,
            'total_duration_ms': 0.0,
            'total_items_processed': 0,
            'total_errors': 0,
            'min_duration_ms': float('inf'),
            'max_duration_ms': 0.0,
            'start_time': time.time()
        }
    
    def record_operation(self, duration_ms: float, success: bool = True, 
                        items_processed: int = 0, errors: int = 0) -> None:
        """Record metrics for a single operation."""
        self.metrics['total_operations'] += 1
        self.metrics['total_duration_ms'] += duration_ms
        self.metrics['total_items_processed'] += items_processed
        self.metrics['total_errors'] += errors
        
        if success:
            self.metrics['successful_operations'] += 1
        else:
            self.metrics['failed_operations'] += 1
        
        # Update min/max duration
        self.metrics['min_duration_ms'] = min(self.metrics['min_duration_ms'], duration_ms)
        self.metrics['max_duration_ms'] = max(self.metrics['max_duration_ms'], duration_ms)
    
    def get_summary(self) -> Dict[str, Any]:
        """Get current performance summary."""
        current_time = time.time()
        total_time_ms = (current_time - self.metrics['start_time']) * 1000
        
        summary = self.metrics.copy()
        summary['total_time_ms'] = total_time_ms
        
        # Calculate derived metrics
        if self.metrics['total_operations'] > 0:
            summary['success_rate'] = self.metrics['successful_operations'] / self.metrics['total_operations']
            summary['failure_rate'] = self.metrics['failed_operations'] / self.metrics['total_operations']
            summary['average_duration_ms'] = self.metrics['total_duration_ms'] / self.metrics['total_operations']
        
        if total_time_ms > 0:
            summary['operations_per_second'] = (self.metrics['total_operations'] * 1000) / total_time_ms
        
        if self.metrics['total_items_processed'] > 0:
            summary['average_items_per_operation'] = self.metrics['total_items_processed'] / self.metrics['total_operations']
            summary['items_per_second'] = (self.metrics['total_items_processed'] * 1000) / total_time_ms
        
        return summary
    
    def log_summary(self) -> None:
        """Log the current performance summary."""
        summary = self.get_summary()
        self.logger.log_performance_summary(self.operation, summary)
    
    def reset(self) -> None:
        """Reset all metrics."""
        self.metrics = {
            'total_operations': 0,
            'successful_operations': 0,
            'failed_operations': 0,
            'total_duration_ms': 0.0,
            'total_items_processed': 0,
            'total_errors': 0,
            'min_duration_ms': float('inf'),
            'max_duration_ms': 0.0,
            'start_time': time.time()
        }


def get_logger(config: Config, name: str = "sonar_ai_agent") -> SonarAILogger:
    """Get or create a logger instance."""
    return SonarAILogger(config, name)