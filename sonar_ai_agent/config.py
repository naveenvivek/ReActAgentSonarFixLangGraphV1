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
        
        # Observability
        self.langfuse_url: str = os.getenv("LANGFUSE_URL", "http://localhost:3000")
        self.langfuse_secret_key: Optional[str] = os.getenv("LANGFUSE_SECRET_KEY")
        self.langfuse_public_key: Optional[str] = os.getenv("LANGFUSE_PUBLIC_KEY")
        
        # Git Configuration
        self.git_user_name: str = os.getenv("GIT_USER_NAME", "SonarQube AI Agent")
        self.git_user_email: str = os.getenv("GIT_USER_EMAIL", "50246903+naveenvivek@users.noreply.github.com")
        self.mr_target_branch: str = os.getenv("MR_TARGET_BRANCH", "main")
        
        # GitHub Configuration
        self.github_token: Optional[str] = os.getenv("GITHUB_TOKEN")
        self.github_username: str = os.getenv("GITHUB_USERNAME", "naveenvivek")
        
        # Validate required environment variables
        self._validate_config()
    
    def _validate_config(self) -> None:
        """Validate that all required environment variables are set."""
        required_vars = [
            ("SONAR_TOKEN", self.sonar_token),
            ("TARGET_REPO_URL", self.target_repo_url),
            ("TARGET_REPO_PATH", self.target_repo_path),
            ("LANGFUSE_SECRET_KEY", self.langfuse_secret_key),
            ("LANGFUSE_PUBLIC_KEY", self.langfuse_public_key),
            ("GITHUB_TOKEN", self.github_token)
        ]
        
        missing_vars = [var_name for var_name, var_value in required_vars if not var_value]
        
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
    
    def __repr__(self) -> str:
        """String representation of config (without sensitive data)."""
        return (
            f"Config("
            f"sonar_url='{self.sonar_url}', "
            f"sonar_project_key='{self.sonar_project_key}', "
            f"target_repo_url='{self.target_repo_url}', "
            f"ollama_url='{self.ollama_url}', "
            f"ollama_model='{self.ollama_model}', "
            f"langfuse_url='{self.langfuse_url}'"
            f")"
        )