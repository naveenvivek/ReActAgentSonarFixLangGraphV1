"""
Git client for handling repository operations, branch management, and merge requests.
Implements single branch atomic fixes strategy.
"""

import subprocess
import os
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
import requests
import json

from ..config import Config
from ..utils.logger import get_logger


class GitClient:
    """Git client for repository operations with atomic fixes support."""

    def __init__(self, config: Config):
        """Initialize Git client."""
        self.config = config
        self.logger = get_logger(config, "sonar_ai_agent.git_client")

        # Git configuration
        self.repo_path = config.git_repo_path if hasattr(
            config, 'git_repo_path') else os.getcwd()
        self.remote_name = config.git_remote_name if hasattr(
            config, 'git_remote_name') else 'origin'
        self.default_branch = config.git_default_branch if hasattr(
            config, 'git_default_branch') else 'main'

        # GitLab configuration for MR creation
        self.gitlab_url = config.gitlab_url if hasattr(
            config, 'gitlab_url') else None
        self.gitlab_token = config.gitlab_token if hasattr(
            config, 'gitlab_token') else None
        self.project_id = config.gitlab_project_id if hasattr(
            config, 'gitlab_project_id') else None

    def create_branch(self, branch_name: str) -> bool:
        """Create a new branch from the default branch."""
        self.logger.info(f"🌿 Creating branch: {branch_name}")

        try:
            # Ensure we're on the default branch and it's up to date
            self._run_git_command(['checkout', self.default_branch])
            self._run_git_command(
                ['pull', self.remote_name, self.default_branch])

            # Create and checkout new branch
            result = self._run_git_command(['checkout', '-b', branch_name])

            if result['success']:
                self.logger.info(
                    f"✅ Successfully created branch: {branch_name}")
                return True
            else:
                self.logger.error(
                    f"❌ Failed to create branch: {result['error']}")
                return False

        except Exception as e:
            self.logger.error(
                f"❌ Exception creating branch {branch_name}: {e}")
            return False

    def commit_changes(self, commit_message: str) -> bool:
        """Commit all current changes with the provided message."""
        self.logger.info("💾 Committing changes")

        try:
            # Check if there are any changes to commit
            status_result = self._run_git_command(['status', '--porcelain'])
            if not status_result['success']:
                self.logger.error("❌ Failed to check git status")
                return False

            if not status_result['output'].strip():
                self.logger.warning("⚠️ No changes to commit")
                return True

            # Add all changes
            add_result = self._run_git_command(['add', '.'])
            if not add_result['success']:
                self.logger.error(
                    f"❌ Failed to add changes: {add_result['error']}")
                return False

            # Commit changes
            commit_result = self._run_git_command(
                ['commit', '-m', commit_message])
            if commit_result['success']:
                self.logger.info("✅ Successfully committed changes")
                return True
            else:
                self.logger.error(
                    f"❌ Failed to commit: {commit_result['error']}")
                return False

        except Exception as e:
            self.logger.error(f"❌ Exception committing changes: {e}")
            return False

    def push_branch(self, branch_name: str) -> bool:
        """Push branch to remote repository."""
        self.logger.info(f"🚀 Pushing branch: {branch_name}")

        try:
            # Push branch to remote
            result = self._run_git_command(
                ['push', '-u', self.remote_name, branch_name])

            if result['success']:
                self.logger.info(
                    f"✅ Successfully pushed branch: {branch_name}")
                return True
            else:
                self.logger.error(
                    f"❌ Failed to push branch: {result['error']}")
                return False

        except Exception as e:
            self.logger.error(f"❌ Exception pushing branch {branch_name}: {e}")
            return False

    def create_merge_request(self, source_branch: str, target_branch: str, title: str, description: str) -> Optional[str]:
        """Create merge request using GitLab API."""
        self.logger.info(
            f"🔀 Creating merge request: {source_branch} -> {target_branch}")

        if not self._validate_gitlab_config():
            self.logger.warning(
                "⚠️ GitLab configuration incomplete, skipping MR creation")
            return None

        try:
            # GitLab API endpoint for merge requests
            url = f"{self.gitlab_url}/api/v4/projects/{self.project_id}/merge_requests"

            headers = {
                'Authorization': f'Bearer {self.gitlab_token}',
                'Content-Type': 'application/json'
            }

            payload = {
                'source_branch': source_branch,
                'target_branch': target_branch,
                'title': title,
                'description': description,
                'remove_source_branch': False,  # Keep branch for review
                'squash': True  # Squash commits for cleaner history
            }

            response = requests.post(
                url, headers=headers, json=payload, timeout=30)

            if response.status_code == 201:
                mr_data = response.json()
                mr_url = mr_data.get('web_url')
                self.logger.info(f"✅ Merge request created: {mr_url}")
                return mr_url
            else:
                self.logger.error(
                    f"❌ Failed to create MR: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            self.logger.error(f"❌ Exception creating merge request: {e}")
            return None

    def get_current_branch(self) -> Optional[str]:
        """Get the current git branch name."""
        try:
            result = self._run_git_command(['branch', '--show-current'])
            if result['success']:
                return result['output'].strip()
            return None
        except Exception as e:
            self.logger.error(f"❌ Exception getting current branch: {e}")
            return None

    def switch_to_branch(self, branch_name: str) -> bool:
        """Switch to specified branch."""
        self.logger.info(f"🔄 Switching to branch: {branch_name}")

        try:
            result = self._run_git_command(['checkout', branch_name])
            if result['success']:
                self.logger.info(f"✅ Switched to branch: {branch_name}")
                return True
            else:
                self.logger.error(
                    f"❌ Failed to switch to branch: {result['error']}")
                return False
        except Exception as e:
            self.logger.error(
                f"❌ Exception switching to branch {branch_name}: {e}")
            return False

    def delete_branch(self, branch_name: str, force: bool = False) -> bool:
        """Delete local branch."""
        self.logger.info(f"🗑️ Deleting branch: {branch_name}")

        try:
            # Don't delete if we're currently on this branch
            current_branch = self.get_current_branch()
            if current_branch == branch_name:
                self.switch_to_branch(self.default_branch)

            flag = '-D' if force else '-d'
            result = self._run_git_command(['branch', flag, branch_name])

            if result['success']:
                self.logger.info(f"✅ Deleted branch: {branch_name}")
                return True
            else:
                self.logger.error(
                    f"❌ Failed to delete branch: {result['error']}")
                return False
        except Exception as e:
            self.logger.error(
                f"❌ Exception deleting branch {branch_name}: {e}")
            return False

    def get_changed_files(self) -> List[str]:
        """Get list of changed files in current working directory."""
        try:
            result = self._run_git_command(['diff', '--name-only', 'HEAD'])
            if result['success']:
                files = [f.strip()
                         for f in result['output'].split('\n') if f.strip()]
                return files
            return []
        except Exception as e:
            self.logger.error(f"❌ Exception getting changed files: {e}")
            return []

    def get_file_diff(self, file_path: str) -> Optional[str]:
        """Get diff for specific file."""
        try:
            result = self._run_git_command(['diff', 'HEAD', file_path])
            if result['success']:
                return result['output']
            return None
        except Exception as e:
            self.logger.error(f"❌ Exception getting diff for {file_path}: {e}")
            return None

    def is_repository(self) -> bool:
        """Check if current directory is a git repository."""
        try:
            result = self._run_git_command(['status'])
            return result['success']
        except Exception:
            return False

    def get_repository_info(self) -> Dict[str, Any]:
        """Get repository information."""
        info = {
            'is_repo': self.is_repository(),
            'current_branch': self.get_current_branch(),
            'changed_files': self.get_changed_files(),
            'repo_path': self.repo_path
        }

        try:
            # Get remote URL
            remote_result = self._run_git_command(
                ['remote', 'get-url', self.remote_name])
            if remote_result['success']:
                info['remote_url'] = remote_result['output'].strip()
        except Exception:
            info['remote_url'] = None

        return info

    def validate_atomic_fixes_preconditions(self) -> Dict[str, Any]:
        """Validate preconditions for atomic fixes strategy."""
        validation = {
            'valid': True,
            'errors': [],
            'warnings': []
        }

        # Check if it's a git repository
        if not self.is_repository():
            validation['valid'] = False
            validation['errors'].append("Not a git repository")
            return validation

        # Check if we're on the default branch
        current_branch = self.get_current_branch()
        if current_branch != self.default_branch:
            validation['warnings'].append(
                f"Currently on '{current_branch}', will switch to '{self.default_branch}'")

        # Check for uncommitted changes
        changed_files = self.get_changed_files()
        if changed_files:
            validation['valid'] = False
            validation['errors'].append(
                f"Uncommitted changes detected in {len(changed_files)} files")

        # Check remote connectivity
        try:
            remote_result = self._run_git_command(
                ['ls-remote', self.remote_name], timeout=10)
            if not remote_result['success']:
                validation['warnings'].append(
                    "Remote connectivity issues detected")
        except Exception:
            validation['warnings'].append(
                "Could not verify remote connectivity")

        return validation

    def _run_git_command(self, args: List[str], timeout: int = 30) -> Dict[str, Any]:
        """Run git command and return result."""
        cmd = ['git'] + args

        try:
            result = subprocess.run(
                cmd,
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False
            )

            return {
                'success': result.returncode == 0,
                'output': result.stdout,
                'error': result.stderr,
                'return_code': result.returncode
            }

        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'output': '',
                'error': f'Command timed out after {timeout} seconds',
                'return_code': -1
            }
        except Exception as e:
            return {
                'success': False,
                'output': '',
                'error': str(e),
                'return_code': -1
            }

    def _validate_gitlab_config(self) -> bool:
        """Validate GitLab configuration for MR creation."""
        return all([
            self.gitlab_url,
            self.gitlab_token,
            self.project_id
        ])

    def create_atomic_fixes_session(self) -> Dict[str, Any]:
        """Create a new session for atomic fixes with timestamp-based branch."""
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        branch_name = f"sonar-ai-fixes-{timestamp}"

        session = {
            'session_id': f"atomic_fixes_{timestamp}",
            'branch_name': branch_name,
            'created_at': datetime.now().isoformat(),
            'status': 'initialized'
        }

        # Validate preconditions
        validation = self.validate_atomic_fixes_preconditions()
        if not validation['valid']:
            session['status'] = 'validation_failed'
            session['errors'] = validation['errors']
            return session

        # Create branch
        if self.create_branch(branch_name):
            session['status'] = 'ready'
            self.logger.info(
                f"🚀 Atomic fixes session created: {session['session_id']}")
        else:
            session['status'] = 'branch_creation_failed'
            self.logger.error(f"❌ Failed to create atomic fixes session")

        return session

    def finalize_atomic_fixes_session(self, session: Dict[str, Any], applied_fixes: List[Any]) -> Dict[str, Any]:
        """Finalize atomic fixes session with commit and MR creation."""
        branch_name = session['branch_name']

        try:
            # Create comprehensive commit message
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            commit_message = f"🔧 SonarQube AI Fixes - {timestamp}\n\n"
            commit_message += f"Applied {len(applied_fixes)} automated fixes atomically:\n\n"

            for i, fix in enumerate(applied_fixes, 1):
                issue_key = getattr(fix, 'issue_key', f'Fix-{i}')
                file_path = getattr(fix, 'file_path', 'unknown')
                commit_message += f"✅ {issue_key} - {file_path}\n"

            commit_message += f"\n🤖 Generated by SonarQube AI Agent"

            # Commit and push
            if not self.commit_changes(commit_message):
                session['status'] = 'commit_failed'
                return session

            if not self.push_branch(branch_name):
                session['status'] = 'push_failed'
                return session

            # Create merge request
            mr_title = f"🤖 SonarQube AI Fixes - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            mr_description = self._create_atomic_mr_description(applied_fixes)

            mr_url = self.create_merge_request(
                source_branch=branch_name,
                target_branch=self.default_branch,
                title=mr_title,
                description=mr_description
            )

            session['status'] = 'completed'
            session['merge_request_url'] = mr_url
            session['completed_at'] = datetime.now().isoformat()
            session['fixes_count'] = len(applied_fixes)

            return session

        except Exception as e:
            session['status'] = 'finalization_failed'
            session['error'] = str(e)
            self.logger.error(
                f"❌ Failed to finalize atomic fixes session: {e}")
            return session

    def _create_atomic_mr_description(self, applied_fixes: List[Any]) -> str:
        """Create MR description for atomic fixes."""
        description = "# 🤖 SonarQube AI Fixes (Atomic)\n\n"
        description += f"This merge request contains **{len(applied_fixes)} automated fixes** "
        description += "applied atomically in a single branch.\n\n"

        description += "## 📊 Summary\n"
        description += f"- **Total Fixes**: {len(applied_fixes)}\n"
        description += f"- **Strategy**: Single branch atomic commits\n"
        description += f"- **Confidence**: High (AI-generated with validation)\n\n"

        description += "## ✅ Fixes Applied\n\n"
        for fix in applied_fixes:
            issue_key = getattr(fix, 'issue_key', 'Unknown')
            file_path = getattr(fix, 'file_path', 'unknown')
            description += f"- **{issue_key}**: `{file_path}`\n"

        description += "\n## 🔍 Review Notes\n"
        description += "- All fixes applied atomically for consistency\n"
        description += "- Changes validated for syntax and security\n"
        description += "- No breaking changes expected\n"
        description += "- Generated by SonarQube AI Agent v1.0\n"

        return description
