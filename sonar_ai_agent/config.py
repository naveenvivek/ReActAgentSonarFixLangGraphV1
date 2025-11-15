"""
Configuration management for SonarQube AI Agent.
"""

import os
from typing import List, Optional
from dotenv import load_dotenv


class Config:
    """Configuration class for SonarQube AI Agent."""

    def __init__(self):
        """Initialize configuration from environment variables."""
        # Load environment variables from .env file
        load_dotenv()

        # SonarQube Configuration
        self.sonar_url = os.getenv('SONAR_URL', 'http://localhost:9000')
        self.sonar_token = os.getenv('SONAR_TOKEN', '')
        self.sonar_project_key = os.getenv('SONAR_PROJECT_KEY', '')

        # Default filters
        self.sonar_default_severities = self._parse_list(
            os.getenv('SONAR_DEFAULT_SEVERITIES', 'BLOCKER,CRITICAL,MAJOR')
        )
        self.sonar_default_types = self._parse_list(
            os.getenv('SONAR_DEFAULT_TYPES', 'BUG,VULNERABILITY,CODE_SMELL')
        )

        # Git Configuration
        self.git_repo_path = os.getenv('GIT_REPO_PATH', os.getcwd())
        self.git_remote_name = os.getenv('GIT_REMOTE_NAME', 'origin')
        self.git_default_branch = os.getenv('GIT_DEFAULT_BRANCH', 'main')

        # GitLab Configuration
        self.gitlab_url = os.getenv('GITLAB_URL')
        self.gitlab_token = os.getenv('GITLAB_TOKEN')
        self.gitlab_project_id = os.getenv('GITLAB_PROJECT_ID')

        # Repository Configuration
        self.target_repo_url = os.getenv(
            'TARGET_REPO_URL', 'https://github.com/example/repo')

        # AWS Bedrock Configuration
        self.bedrock_region = os.getenv('BEDROCK_REGION', 'us-east-1')
        self.bedrock_model_id = os.getenv(
            'BEDROCK_MODEL_ID', 'anthropic.claude-3-haiku-20240307-v1:0')
        self.aws_access_key_id = os.getenv('AWS_ACCESS_KEY_ID')
        self.aws_secret_access_key = os.getenv('AWS_SECRET_ACCESS_KEY')

        # Langfuse Configuration (if using)
        self.langfuse_secret_key = os.getenv('LANGFUSE_SECRET_KEY')
        self.langfuse_public_key = os.getenv('LANGFUSE_PUBLIC_KEY')
        self.langfuse_host = os.getenv('LANGFUSE_HOST')

        # Logging Configuration
        self.log_file = os.getenv('LOG_FILE', 'logs/sonar_ai_agent.log')
        self.log_level = os.getenv('LOG_LEVEL', 'INFO')

        # Agent Configuration
        self.use_ai_analysis = self._parse_bool(
            os.getenv('USE_AI_ANALYSIS', 'true'))
        self.validate_syntax = self._parse_bool(
            os.getenv('VALIDATE_SYNTAX', 'true'))
        self.validate_security = self._parse_bool(
            os.getenv('VALIDATE_SECURITY', 'true'))
        self.backup_files = self._parse_bool(os.getenv('BACKUP_FILES', 'true'))

        # Workflow Configuration
        self.max_issues_per_run = int(os.getenv('MAX_ISSUES_PER_RUN', '50'))
        self.batch_size = int(os.getenv('BATCH_SIZE', '10'))

        # Ensure log directory exists
        os.makedirs(os.path.dirname(self.log_file), exist_ok=True)

    def _parse_list(self, value: str) -> List[str]:
        """Parse comma-separated string to list."""
        if not value:
            return []
        return [item.strip() for item in value.split(',') if item.strip()]

    def _parse_bool(self, value: str) -> bool:
        """Parse string to boolean."""
        return value.lower() in ('true', '1', 'yes', 'on')

    def validate(self) -> List[str]:
        """Validate configuration and return list of errors."""
        errors = []

        # Required SonarQube settings
        if not self.sonar_url:
            errors.append("SONAR_URL is required")
        if not self.sonar_token:
            errors.append("SONAR_TOKEN is required")
        if not self.sonar_project_key:
            errors.append("SONAR_PROJECT_KEY is required")

        # AWS Bedrock settings (if using AI)
        if self.use_ai_analysis:
            if not self.aws_access_key_id:
                errors.append("AWS_ACCESS_KEY_ID is required for AI analysis")
            if not self.aws_secret_access_key:
                errors.append(
                    "AWS_SECRET_ACCESS_KEY is required for AI analysis")

        return errors

    def get_sonar_config(self) -> dict:
        """Get SonarQube configuration as dictionary."""
        return {
            'url': self.sonar_url,
            'token': self.sonar_token,
            'project_key': self.sonar_project_key,
            'default_severities': self.sonar_default_severities,
            'default_types': self.sonar_default_types
        }

    def get_git_config(self) -> dict:
        """Get Git configuration as dictionary."""
        return {
            'repo_path': self.git_repo_path,
            'remote_name': self.git_remote_name,
            'default_branch': self.git_default_branch,
            'gitlab_url': self.gitlab_url,
            'gitlab_token': self.gitlab_token,
            'project_id': self.gitlab_project_id
        }

    def get_bedrock_config(self) -> dict:
        """Get AWS Bedrock configuration as dictionary."""
        return {
            'region': self.bedrock_region,
            'model_id': self.bedrock_model_id,
            'access_key_id': self.aws_access_key_id,
            'secret_access_key': self.aws_secret_access_key
        }

    def __str__(self) -> str:
        """String representation of configuration (without sensitive data)."""
        return f"""SonarQube AI Agent Configuration:
  SonarQube URL: {self.sonar_url}
  Project Key: {self.sonar_project_key}
  Repository: {self.target_repo_url}
  Model: {self.bedrock_model_id}
  Log File: {self.log_file}
  Use AI: {self.use_ai_analysis}
  Validate Syntax: {self.validate_syntax}
  Backup Files: {self.backup_files}
"""
