"""
Git client for repository operations used by the Bug Hunter Agent.
Handles cloning, code reading, and branch management.
"""

import os
import subprocess
import logging
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import shutil

from ..config import Config


class GitClient:
    """Client for Git repository operations."""
    
    def __init__(self, config: Config):
        """Initialize Git client with configuration."""
        self.config = config
        self.repo_url = config.target_repo_url
        self.repo_path = Path(config.target_repo_path)
        self.default_branch = config.target_repo_branch
        
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        
        # Add console handler if not exists
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setLevel(logging.DEBUG)
            formatter = logging.Formatter('%(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
    
    def clone_repository(self, force_refresh: bool = False) -> bool:
        """
        Clone the target repository if it doesn't exist, or update if it does.
        
        Args:
            force_refresh: If True, delete existing repo and clone fresh
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if self.repo_path.exists():
                if force_refresh:
                    self.logger.info(f"Removing existing repository at {self.repo_path}")
                    shutil.rmtree(self.repo_path)
                else:
                    self.logger.info(f"Repository already exists at {self.repo_path}, updating...")
                    return self.update_repository()
            
            # Clone the repository
            self.logger.info(f"Cloning repository {self.repo_url} to {self.repo_path}")
            
            # Ensure parent directory exists
            self.repo_path.parent.mkdir(parents=True, exist_ok=True)
            
            result = subprocess.run([
                'git', 'clone', self.repo_url, str(self.repo_path)
            ], capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                self.logger.info(f"Successfully cloned repository to {self.repo_path}")
                return True
            else:
                self.logger.error(f"Failed to clone repository: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            self.logger.error("Repository clone timed out")
            return False
        except Exception as e:
            self.logger.error(f"Error cloning repository: {e}")
            return False
    
    def update_repository(self) -> bool:
        """Update the existing repository to latest changes."""
        try:
            if not self.repo_path.exists():
                self.logger.warning("Repository doesn't exist, cloning instead")
                return self.clone_repository()
            
            self.logger.info(f"Updating repository at {self.repo_path}")
            
            # Change to repository directory and pull latest changes
            result = subprocess.run([
                'git', 'pull', 'origin', self.default_branch
            ], cwd=self.repo_path, capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0:
                self.logger.info("Successfully updated repository")
                return True
            else:
                self.logger.error(f"Failed to update repository: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            self.logger.error("Repository update timed out")
            return False
        except Exception as e:
            self.logger.error(f"Error updating repository: {e}")
            return False
    
    def read_file_content(self, file_path: str, start_line: int = 1, end_line: Optional[int] = None) -> str:
        """
        Read content from a file in the repository.
        
        Args:
            file_path: Relative path to file from repository root
            start_line: Starting line number (1-based)
            end_line: Ending line number (inclusive), None for end of file
            
        Returns:
            File content as string
        """
        try:
            full_path = self.repo_path / file_path
            
            if not full_path.exists():
                self.logger.warning(f"File not found: {file_path}")
                return ""
            
            with open(full_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # Convert to 0-based indexing
            start_idx = max(0, start_line - 1)
            end_idx = len(lines) if end_line is None else min(len(lines), end_line)
            
            selected_lines = lines[start_idx:end_idx]
            content = ''.join(selected_lines)
            
            self.logger.debug(f"Read {len(selected_lines)} lines from {file_path}")
            return content
            
        except Exception as e:
            self.logger.error(f"Error reading file {file_path}: {e}")
            return ""
    
    def get_file_context(self, file_path: str, target_line: int, context_lines: int = 10) -> Dict[str, any]:
        """
        Get code context around a specific line in a file.
        
        Args:
            file_path: Relative path to file from repository root
            target_line: Line number of interest
            context_lines: Number of lines before and after to include
            
        Returns:
            Dictionary with file context information
        """
        try:
            full_path = self.repo_path / file_path
            
            if not full_path.exists():
                self.logger.warning(f"File not found: {file_path}")
                return {}
            
            with open(full_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            total_lines = len(lines)
            start_line = max(1, target_line - context_lines)
            end_line = min(total_lines, target_line + context_lines)
            
            # Get the context
            context_content = self.read_file_content(file_path, start_line, end_line)
            
            # Get the specific line
            target_content = lines[target_line - 1].strip() if target_line <= total_lines else ""
            
            return {
                'file_path': file_path,
                'target_line': target_line,
                'target_content': target_content,
                'context_start_line': start_line,
                'context_end_line': end_line,
                'context_content': context_content,
                'total_lines': total_lines,
                'language': self._detect_language(file_path)
            }
            
        except Exception as e:
            self.logger.error(f"Error getting file context for {file_path}:{target_line}: {e}")
            return {}
    
    def _detect_language(self, file_path: str) -> str:
        """Detect programming language from file extension."""
        extension = Path(file_path).suffix.lower()
        
        language_map = {
            '.java': 'java',
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.cpp': 'cpp',
            '.c': 'c',
            '.cs': 'csharp',
            '.php': 'php',
            '.rb': 'ruby',
            '.go': 'go',
            '.rs': 'rust',
            '.kt': 'kotlin',
            '.scala': 'scala',
            '.xml': 'xml',
            '.json': 'json',
            '.yml': 'yaml',
            '.yaml': 'yaml',
            '.properties': 'properties',
            '.sql': 'sql'
        }
        
        return language_map.get(extension, 'text')
    
    def create_branch(self, branch_name: str, from_branch: Optional[str] = None) -> bool:
        """
        Create a new branch in the repository.
        
        Args:
            branch_name: Name of the new branch
            from_branch: Source branch (defaults to default branch)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.repo_path.exists():
                self.logger.error("Repository doesn't exist")
                return False
            
            from_branch = from_branch or self.default_branch
            
            # Ensure we're on the source branch and it's up to date
            subprocess.run([
                'git', 'checkout', from_branch
            ], cwd=self.repo_path, capture_output=True, text=True)
            
            subprocess.run([
                'git', 'pull', 'origin', from_branch
            ], cwd=self.repo_path, capture_output=True, text=True)
            
            # Create and checkout new branch
            result = subprocess.run([
                'git', 'checkout', '-b', branch_name
            ], cwd=self.repo_path, capture_output=True, text=True)
            
            if result.returncode == 0:
                self.logger.info(f"Created branch: {branch_name}")
                return True
            else:
                self.logger.error(f"Failed to create branch {branch_name}: {result.stderr}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error creating branch {branch_name}: {e}")
            return False
    
    def commit_changes(self, files: List[str], commit_message: str) -> bool:
        """
        Commit changes to the current branch.
        
        Args:
            files: List of file paths to commit
            commit_message: Commit message
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.repo_path.exists():
                self.logger.error("Repository doesn't exist")
                return False
            
            # Configure git user if not already set
            self._configure_git_user()
            
            # Add files
            for file_path in files:
                result = subprocess.run([
                    'git', 'add', file_path
                ], cwd=self.repo_path, capture_output=True, text=True)
                
                if result.returncode != 0:
                    self.logger.error(f"Failed to add file {file_path}: {result.stderr}")
                    return False
            
            # Commit changes
            result = subprocess.run([
                'git', 'commit', '-m', commit_message
            ], cwd=self.repo_path, capture_output=True, text=True)
            
            if result.returncode == 0:
                self.logger.info(f"Committed changes: {commit_message}")
                return True
            else:
                self.logger.error(f"Failed to commit changes: {result.stderr}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error committing changes: {e}")
            return False
    
    def push_branch(self, branch_name: str) -> bool:
        """
        Push branch to remote repository.
        
        Args:
            branch_name: Name of the branch to push
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.repo_path.exists():
                self.logger.error("Repository doesn't exist")
                return False
            
            result = subprocess.run([
                'git', 'push', 'origin', branch_name
            ], cwd=self.repo_path, capture_output=True, text=True)
            
            if result.returncode == 0:
                self.logger.info(f"Pushed branch: {branch_name}")
                return True
            else:
                self.logger.error(f"Failed to push branch {branch_name}: {result.stderr}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error pushing branch {branch_name}: {e}")
            return False
    
    def _configure_git_user(self):
        """Configure git user name and email if not already set."""
        try:
            # Check if user.name is set
            result = subprocess.run([
                'git', 'config', 'user.name'
            ], cwd=self.repo_path, capture_output=True, text=True)
            
            if result.returncode != 0:
                subprocess.run([
                    'git', 'config', 'user.name', self.config.git_user_name
                ], cwd=self.repo_path, capture_output=True, text=True)
            
            # Check if user.email is set
            result = subprocess.run([
                'git', 'config', 'user.email'
            ], cwd=self.repo_path, capture_output=True, text=True)
            
            if result.returncode != 0:
                subprocess.run([
                    'git', 'config', 'user.email', self.config.git_user_email
                ], cwd=self.repo_path, capture_output=True, text=True)
                
        except Exception as e:
            self.logger.warning(f"Could not configure git user: {e}")
    
    def get_current_branch(self) -> str:
        """Get the name of the current branch."""
        try:
            if not self.repo_path.exists():
                return ""
            
            result = subprocess.run([
                'git', 'branch', '--show-current'
            ], cwd=self.repo_path, capture_output=True, text=True)
            
            if result.returncode == 0:
                return result.stdout.strip()
            else:
                return ""
                
        except Exception as e:
            self.logger.error(f"Error getting current branch: {e}")
            return ""
    
    def list_files(self, pattern: str = "*", directory: str = "") -> List[str]:
        """
        List files in the repository matching a pattern.
        
        Args:
            pattern: File pattern to match (e.g., "*.java")
            directory: Directory to search in (relative to repo root)
            
        Returns:
            List of file paths relative to repository root
        """
        try:
            search_path = self.repo_path / directory if directory else self.repo_path
            
            if not search_path.exists():
                return []
            
            from glob import glob
            import os
            
            # Change to search directory
            old_cwd = os.getcwd()
            os.chdir(search_path)
            
            try:
                # Find files matching pattern
                files = glob(pattern, recursive=True)
                
                # Convert to relative paths from repo root
                if directory:
                    files = [os.path.join(directory, f) for f in files]
                
                return files
            finally:
                os.chdir(old_cwd)
                
        except Exception as e:
            self.logger.error(f"Error listing files: {e}")
            return []
    
    def get_repository_info(self) -> Dict[str, str]:
        """Get basic repository information."""
        try:
            if not self.repo_path.exists():
                return {}
            
            # Get remote URL
            result = subprocess.run([
                'git', 'remote', 'get-url', 'origin'
            ], cwd=self.repo_path, capture_output=True, text=True)
            
            remote_url = result.stdout.strip() if result.returncode == 0 else ""
            
            # Get current commit hash
            result = subprocess.run([
                'git', 'rev-parse', 'HEAD'
            ], cwd=self.repo_path, capture_output=True, text=True)
            
            commit_hash = result.stdout.strip() if result.returncode == 0 else ""
            
            return {
                'path': str(self.repo_path),
                'remote_url': remote_url,
                'current_branch': self.get_current_branch(),
                'commit_hash': commit_hash[:8] if commit_hash else "",
                'default_branch': self.default_branch
            }
            
        except Exception as e:
            self.logger.error(f"Error getting repository info: {e}")
            return {}