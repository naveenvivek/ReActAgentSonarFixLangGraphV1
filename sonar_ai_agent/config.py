"""
Configuration management for SonarQube AI Agent system.
Loads settings from environment variables with validation.
"""

import os
from dataclasses import dataclass
from typing import Optional
from dotenv import load_dotenv


@dataclass
class Config:
    """Configuration class for SonarQube AI Agent system."""
    
    def __init__(self):
        """Initialize configuration from environment variables."""
        # Load environment variables from .env file
        load_dotenv()
        
        # SonarQube Configuration
        self.sonar_url: str = os.getenv("SONAR_URL", "http://localhost:9100")
        self.sonar_token: Optional[str] = os.getenv("SONAR_TOKEN")
        self.sonar_project_key: str = os.getenv("SONAR_PROJECT_KEY", "naveenvivek_SpringBootAppSonarAI")
        
        # Target Application Repository
        self.target_repo_url: Optional[str] = os.getenv("TARGET_REPO_URL")
        self.target_repo_path: Optional[str] = os.getenv("TARGET_REPO_PATH")
        self.target_repo_branch: str = os.getenv("TARGET_REPO_BRANCH", "main")
        
        # AI Configuration
        self.ollama_url: str = os.getenv("OLLAMA_URL", "http://localhost:11434")
        self.ollama_model: str = os.getenv("OLLAMA_MODEL", "llama3.1:latest")
        
        # Logging Configuration
        self.log_level: str = os.getenv("LOG_LEVEL", "INFO")
        self.log_file: str = os.getenv("LOG_FILE", "logs/sonar_ai_agent.log")
        self.log_max_size: int = int(os.getenv("LOG_MAX_SIZE", "10485760"))  # 10MB default
        self.log_backup_count: int = int(os.getenv("LOG_BACKUP_COUNT", "5"))
        
        # Structured Logging Configuration
        self.structured_logging_enabled: bool = os.getenv("STRUCTURED_LOGGING_ENABLED", "true").lower() == "true"
        self.console_color_enabled: bool = os.getenv("CONSOLE_COLOR_ENABLED", "true").lower() == "true"
        self.metadata_max_depth: int = int(os.getenv("METADATA_MAX_DEPTH", "3"))
        self.metadata_max_length: int = int(os.getenv("METADATA_MAX_LENGTH", "1000"))
        self.performance_logging_enabled: bool = os.getenv("PERFORMANCE_LOGGING_ENABLED", "true").lower() == "true"
        self.error_stack_trace_enabled: bool = os.getenv("ERROR_STACK_TRACE_ENABLED", "true").lower() == "true"
        self.correlation_tracking_enabled: bool = os.getenv("CORRELATION_TRACKING_ENABLED", "true").lower() == "true"
        
        # Performance Thresholds
        self.slow_operation_threshold_ms: int = int(os.getenv("SLOW_OPERATION_THRESHOLD_MS", "5000"))  # 5 seconds
        self.very_slow_operation_threshold_ms: int = int(os.getenv("VERY_SLOW_OPERATION_THRESHOLD_MS", "10000"))  # 10 seconds
        self.low_throughput_threshold: float = float(os.getenv("LOW_THROUGHPUT_THRESHOLD", "1.0"))  # items per second
        self.high_error_rate_threshold: float = float(os.getenv("HIGH_ERROR_RATE_THRESHOLD", "0.1"))  # 10% error rate
        
        # Git Configuration
        self.git_user_name: str = os.getenv("GIT_USER_NAME", "SonarQube AI Agent")
        self.git_user_email: str = os.getenv("GIT_USER_EMAIL", "50246903+naveenvivek@users.noreply.github.com")
        self.mr_target_branch: str = os.getenv("MR_TARGET_BRANCH", "main")
        
        # GitHub Configuration
        self.github_token: Optional[str] = os.getenv("GITHUB_TOKEN")
        self.github_username: str = os.getenv("GITHUB_USERNAME", "naveenvivek")
        
        # Validate required environment variables
        self._validate_config()
        
        # Validate structured logging configuration
        self._validate_logging_config()
    
    def _validate_config(self) -> None:
        """Validate that all required environment variables are set."""
        required_vars = [
            ("SONAR_TOKEN", self.sonar_token),
            ("TARGET_REPO_URL", self.target_repo_url),
            ("TARGET_REPO_PATH", self.target_repo_path),
            ("GITHUB_TOKEN", self.github_token)
        ]
        
        missing_vars = [var_name for var_name, var_value in required_vars if not var_value]
        
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
    
    def _validate_logging_config(self) -> None:
        """Validate structured logging configuration parameters."""
        # Validate metadata depth
        if self.metadata_max_depth < 1 or self.metadata_max_depth > 10:
            raise ValueError("METADATA_MAX_DEPTH must be between 1 and 10")
        
        # Validate metadata length
        if self.metadata_max_length < 100 or self.metadata_max_length > 10000:
            raise ValueError("METADATA_MAX_LENGTH must be between 100 and 10000")
        
        # Validate performance thresholds
        if self.slow_operation_threshold_ms < 100:
            raise ValueError("SLOW_OPERATION_THRESHOLD_MS must be at least 100ms")
        
        if self.very_slow_operation_threshold_ms <= self.slow_operation_threshold_ms:
            raise ValueError("VERY_SLOW_OPERATION_THRESHOLD_MS must be greater than SLOW_OPERATION_THRESHOLD_MS")
        
        if self.low_throughput_threshold < 0:
            raise ValueError("LOW_THROUGHPUT_THRESHOLD must be non-negative")
        
        if self.high_error_rate_threshold < 0 or self.high_error_rate_threshold > 1:
            raise ValueError("HIGH_ERROR_RATE_THRESHOLD must be between 0 and 1")
    
    def __repr__(self) -> str:
        """String representation of config (without sensitive data)."""
        return (
            f"Config("
            f"sonar_url='{self.sonar_url}', "
            f"sonar_project_key='{self.sonar_project_key}', "
            f"target_repo_url='{self.target_repo_url}', "
            f"ollama_url='{self.ollama_url}', "
            f"ollama_model='{self.ollama_model}', "
            f"log_file='{self.log_file}', "
            f"structured_logging={self.structured_logging_enabled}, "
            f"performance_logging={self.performance_logging_enabled}"
            f")"
        )