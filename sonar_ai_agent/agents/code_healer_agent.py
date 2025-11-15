"""
Code Healer Agent - Applies SonarQube fixes to source code.
Implements automated code healing with validation and metrics tracking.
"""

import os
import re
import ast
import json
import time
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
import tempfile
import shutil
import subprocess

from ..models import FixPlan, AgentMetrics
from ..config import Config
from ..utils.logger import get_logger


class CodeHealerAgent:
    """Agent responsible for applying SonarQube fixes to source code."""

    def __init__(self, config: Config):
        """Initialize Code Healer Agent."""
        self.config = config

        # Initialize file-based logger
        self.logger = get_logger(config, "sonar_ai_agent.code_healer_agent")

        # Metrics tracking
        self.metrics = None
        self.start_time = None

        # Validation settings
        self.validate_syntax = config.validate_syntax if hasattr(
            config, 'validate_syntax') else True
        self.validate_security = config.validate_security if hasattr(
            config, 'validate_security') else True
        self.backup_files = config.backup_files if hasattr(
            config, 'backup_files') else True

    def apply_fix(self, fix_plan: FixPlan) -> Dict[str, Any]:
        """Apply a single fix plan to the source code."""
        self.logger.info(f"🔧 Applying fix for issue: {fix_plan.issue_key}")

        start_time = time.time()

        try:
            # Validate fix plan
            if not self._validate_fix_plan(fix_plan):
                return {
                    "success": False,
                    "error": "Invalid fix plan",
                    "issue_key": fix_plan.issue_key
                }

            # Check if file exists
            if not os.path.exists(fix_plan.file_path):
                return {
                    "success": False,
                    "error": f"File not found: {fix_plan.file_path}",
                    "issue_key": fix_plan.issue_key
                }

            # Create backup if enabled
            backup_path = None
            if self.backup_files:
                backup_path = self._create_backup(fix_plan.file_path)

            # Read original file
            original_content = self._read_file(fix_plan.file_path)
            if original_content is None:
                return {
                    "success": False,
                    "error": f"Could not read file: {fix_plan.file_path}",
                    "issue_key": fix_plan.issue_key
                }

            # Apply the fix
            fixed_content = self._apply_fix_to_content(
                original_content, fix_plan)
            if fixed_content is None:
                return {
                    "success": False,
                    "error": "Failed to apply fix to content",
                    "issue_key": fix_plan.issue_key
                }

            # Validate fixed content
            validation_result = self._validate_fixed_content(
                fixed_content,
                fix_plan.file_path,
                original_content
            )

            if not validation_result["valid"]:
                return {
                    "success": False,
                    "error": f"Validation failed: {validation_result['errors']}",
                    "issue_key": fix_plan.issue_key
                }

            # Write fixed content to file
            if not self._write_file(fix_plan.file_path, fixed_content):
                return {
                    "success": False,
                    "error": f"Could not write to file: {fix_plan.file_path}",
                    "issue_key": fix_plan.issue_key
                }

            # Calculate metrics
            processing_time = time.time() - start_time
            lines_changed = self._count_changed_lines(
                original_content, fixed_content)

            result = {
                "success": True,
                "issue_key": fix_plan.issue_key,
                "file_path": fix_plan.file_path,
                "lines_changed": lines_changed,
                "processing_time": processing_time,
                "backup_path": backup_path,
                "confidence_score": fix_plan.confidence_score,
                "fix_type": getattr(fix_plan, 'fix_type', 'unknown'),
                "severity": getattr(fix_plan, 'severity', 'unknown')
            }

            self.logger.info(
                f"✅ Successfully applied fix: {fix_plan.issue_key}")
            return result

        except Exception as e:
            self.logger.error(
                f"❌ Exception applying fix {fix_plan.issue_key}: {e}")
            return {
                "success": False,
                "error": str(e),
                "issue_key": fix_plan.issue_key
            }

    def validate_changes(self) -> Dict[str, Any]:
        """Validate all changes made during the current session."""
        self.logger.info("🔍 Validating all applied changes")

        try:
            validation_results = {
                "valid": True,
                "errors": [],
                "warnings": [],
                "syntax_valid": True,
                "security_valid": True
            }

            # Check for Python syntax errors across all changed files
            if self.validate_syntax:
                syntax_result = self._validate_python_syntax()
                validation_results["syntax_valid"] = syntax_result["valid"]
                if not syntax_result["valid"]:
                    validation_results["errors"].extend(
                        syntax_result["errors"])

            # Run security validation
            if self.validate_security:
                security_result = self._validate_security()
                validation_results["security_valid"] = security_result["valid"]
                if security_result["warnings"]:
                    validation_results["warnings"].extend(
                        security_result["warnings"])

            # Overall validation
            validation_results["valid"] = (
                validation_results["syntax_valid"] and
                validation_results["security_valid"]
            )

            if validation_results["valid"]:
                self.logger.info("✅ All changes validated successfully")
            else:
                self.logger.warning(
                    f"⚠️ Validation issues found: {validation_results['errors']}")

            return validation_results

        except Exception as e:
            self.logger.error(f"❌ Validation error: {e}")
            return {
                "valid": False,
                "errors": [str(e)],
                "warnings": [],
                "syntax_valid": False,
                "security_valid": False
            }

    def start_metrics_tracking(self):
        """Start tracking metrics for the Code Healer session."""
        self.start_time = time.time()
        self.metrics = AgentMetrics(
            agent_name="CodeHealerAgent",
            start_time=datetime.now(),
            end_time=None,
            processing_time_seconds=0,
            issues_processed=0,
            fixes_applied=0,
            success_rate=0.0,
            confidence_scores=[],
            errors=[]
        )
        self.logger.info("📊 Started metrics tracking for Code Healer")

    def stop_metrics_tracking(self) -> Optional[AgentMetrics]:
        """Stop metrics tracking and return results."""
        if self.metrics and self.start_time:
            self.metrics.end_time = datetime.now()
            self.metrics.processing_time_seconds = time.time() - self.start_time
            self.logger.info("📊 Stopped metrics tracking for Code Healer")
            return self.metrics
        return None

    def _validate_fix_plan(self, fix_plan: FixPlan) -> bool:
        """Validate fix plan completeness and consistency."""
        required_fields = [
            'issue_key', 'file_path', 'line_number',
            'issue_description', 'proposed_solution', 'confidence_score'
        ]

        for field in required_fields:
            if not hasattr(fix_plan, field) or not getattr(fix_plan, field):
                self.logger.warning(
                    f"⚠️ Fix plan missing required field: {field}")
                return False

        # Validate confidence score
        if not (0.0 <= fix_plan.confidence_score <= 1.0):
            self.logger.warning(
                f"⚠️ Invalid confidence score: {fix_plan.confidence_score}")
            return False

        return True

    def _create_backup(self, file_path: str) -> Optional[str]:
        """Create backup of file before modification."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_dir = os.path.join(
                os.path.dirname(file_path), ".sonar_backups")
            os.makedirs(backup_dir, exist_ok=True)

            filename = os.path.basename(file_path)
            backup_filename = f"{filename}.{timestamp}.backup"
            backup_path = os.path.join(backup_dir, backup_filename)

            shutil.copy2(file_path, backup_path)
            self.logger.debug(f"💾 Created backup: {backup_path}")
            return backup_path

        except Exception as e:
            self.logger.warning(
                f"⚠️ Could not create backup for {file_path}: {e}")
            return None

    def _read_file(self, file_path: str) -> Optional[str]:
        """Read file content safely."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            self.logger.error(f"❌ Could not read file {file_path}: {e}")
            return None

    def _write_file(self, file_path: str, content: str) -> bool:
        """Write content to file safely."""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        except Exception as e:
            self.logger.error(f"❌ Could not write file {file_path}: {e}")
            return False

    def _apply_fix_to_content(self, content: str, fix_plan: FixPlan) -> Optional[str]:
        """Apply fix to file content based on the fix plan."""
        try:
            lines = content.split('\n')

            # Validate line number
            if fix_plan.line_number < 1 or fix_plan.line_number > len(lines):
                self.logger.error(
                    f"❌ Invalid line number {fix_plan.line_number} for file with {len(lines)} lines")
                return None

            # Get the fix type and apply appropriate transformation
            fix_type = getattr(fix_plan, 'fix_type', 'replace')

            if fix_type == 'replace':
                return self._apply_replace_fix(lines, fix_plan)
            elif fix_type == 'insert':
                return self._apply_insert_fix(lines, fix_plan)
            elif fix_type == 'delete':
                return self._apply_delete_fix(lines, fix_plan)
            elif fix_type == 'regex':
                return self._apply_regex_fix(content, fix_plan)
            else:
                # Default to intelligent fix application
                return self._apply_intelligent_fix(lines, fix_plan)

        except Exception as e:
            self.logger.error(f"❌ Exception applying fix: {e}")
            return None

    def _apply_replace_fix(self, lines: List[str], fix_plan: FixPlan) -> str:
        """Apply a replace-type fix."""
        line_index = fix_plan.line_number - 1

        # Extract the new line content from proposed solution
        new_content = self._extract_fix_content(fix_plan.proposed_solution)

        # Preserve indentation from original line
        original_line = lines[line_index]
        indentation = self._get_line_indentation(original_line)

        # Apply indentation to new content
        if new_content.strip():
            lines[line_index] = indentation + new_content.strip()
        else:
            lines[line_index] = new_content

        return '\n'.join(lines)

    def _apply_insert_fix(self, lines: List[str], fix_plan: FixPlan) -> str:
        """Apply an insert-type fix."""
        line_index = fix_plan.line_number - 1

        # Extract the content to insert
        new_content = self._extract_fix_content(fix_plan.proposed_solution)

        # Get indentation from surrounding lines
        indentation = self._get_contextual_indentation(lines, line_index)

        # Insert new line
        new_line = indentation + new_content.strip() if new_content.strip() else new_content
        lines.insert(line_index, new_line)

        return '\n'.join(lines)

    def _apply_delete_fix(self, lines: List[str], fix_plan: FixPlan) -> str:
        """Apply a delete-type fix."""
        line_index = fix_plan.line_number - 1

        # Remove the line
        if 0 <= line_index < len(lines):
            lines.pop(line_index)

        return '\n'.join(lines)

    def _apply_regex_fix(self, content: str, fix_plan: FixPlan) -> str:
        """Apply a regex-based fix."""
        try:
            # Extract pattern and replacement from proposed solution
            solution = fix_plan.proposed_solution

            # Look for patterns like "Replace: pattern -> replacement"
            if " -> " in solution:
                parts = solution.split(" -> ", 1)
                if len(parts) == 2:
                    pattern = parts[0].replace("Replace: ", "").strip()
                    replacement = parts[1].strip()

                    # Apply regex replacement
                    fixed_content = re.sub(
                        pattern, replacement, content, flags=re.MULTILINE)
                    return fixed_content

            # Fallback to line-based fix
            lines = content.split('\n')
            return self._apply_intelligent_fix(lines, fix_plan)

        except Exception as e:
            self.logger.warning(
                f"⚠️ Regex fix failed, falling back to intelligent fix: {e}")
            lines = content.split('\n')
            return self._apply_intelligent_fix(lines, fix_plan)

    def _apply_intelligent_fix(self, lines: List[str], fix_plan: FixPlan) -> str:
        """Apply an intelligent fix based on issue description and solution."""
        line_index = fix_plan.line_number - 1
        original_line = lines[line_index]

        # Analyze the issue and proposed solution
        issue_desc = fix_plan.issue_description.lower()
        solution = fix_plan.proposed_solution.lower()

        # Common SonarQube issue patterns and fixes
        if "unused import" in issue_desc or "unused variable" in issue_desc:
            # Remove the line
            lines.pop(line_index)
        elif "missing" in solution or "add" in solution:
            # Insert new content
            new_content = self._extract_fix_content(fix_plan.proposed_solution)
            indentation = self._get_line_indentation(original_line)
            new_line = indentation + new_content.strip()
            lines.insert(line_index, new_line)
        elif "replace" in solution or "change" in solution:
            # Replace content
            new_content = self._extract_fix_content(fix_plan.proposed_solution)
            indentation = self._get_line_indentation(original_line)
            lines[line_index] = indentation + new_content.strip()
        else:
            # Default to content extraction from solution
            new_content = self._extract_fix_content(fix_plan.proposed_solution)
            if new_content and new_content != original_line.strip():
                indentation = self._get_line_indentation(original_line)
                lines[line_index] = indentation + new_content.strip()

        return '\n'.join(lines)

    def _extract_fix_content(self, proposed_solution: str) -> str:
        """Extract the actual code content from proposed solution."""
        # Remove common prefixes and explanatory text
        solution = proposed_solution.strip()

        # Remove common solution prefixes
        prefixes_to_remove = [
            "Replace with:", "Change to:", "Use:", "Replace line with:",
            "Fix:", "Solution:", "Correction:", "Updated code:"
        ]

        for prefix in prefixes_to_remove:
            if solution.lower().startswith(prefix.lower()):
                solution = solution[len(prefix):].strip()
                break

        # Extract code from code blocks
        if "```" in solution:
            # Extract from code block
            parts = solution.split("```")
            if len(parts) >= 3:
                # Get the code block content
                code_block = parts[1]
                # Remove language identifier
                lines = code_block.strip().split('\n')
                if lines and not lines[0].strip().startswith(('import', 'def', 'class', 'if', 'for', 'while')):
                    lines = lines[1:]  # Remove language identifier
                return '\n'.join(lines).strip()

        # Remove quotes if the entire solution is quoted
        if solution.startswith('"') and solution.endswith('"'):
            solution = solution[1:-1]
        elif solution.startswith("'") and solution.endswith("'"):
            solution = solution[1:-1]

        return solution

    def _get_line_indentation(self, line: str) -> str:
        """Get the indentation (leading whitespace) of a line."""
        return line[:len(line) - len(line.lstrip())]

    def _get_contextual_indentation(self, lines: List[str], line_index: int) -> str:
        """Get appropriate indentation based on surrounding context."""
        # Check previous non-empty line
        for i in range(line_index - 1, -1, -1):
            if lines[i].strip():
                return self._get_line_indentation(lines[i])

        # Check next non-empty line
        for i in range(line_index + 1, len(lines)):
            if lines[i].strip():
                return self._get_line_indentation(lines[i])

        return ""

    def _validate_fixed_content(self, content: str, file_path: str, original_content: str) -> Dict[str, Any]:
        """Validate the fixed content for syntax and other issues."""
        validation = {
            "valid": True,
            "errors": [],
            "warnings": []
        }

        # Check for Python syntax if it's a Python file
        if file_path.endswith('.py'):
            try:
                ast.parse(content)
            except SyntaxError as e:
                validation["valid"] = False
                validation["errors"].append(f"Python syntax error: {e}")

        # Check that content was actually changed
        if content == original_content:
            validation["warnings"].append(
                "Content unchanged after fix application")

        # Check for common issues
        lines = content.split('\n')
        for i, line in enumerate(lines, 1):
            # Check for obvious syntax issues
            stripped = line.strip()
            if stripped.endswith(',,') or stripped.endswith(';;'):
                validation["warnings"].append(
                    f"Line {i}: Potential syntax issue with double punctuation")

        return validation

    def _validate_python_syntax(self) -> Dict[str, Any]:
        """Validate Python syntax across all Python files in the current directory."""
        result = {
            "valid": True,
            "errors": []
        }

        try:
            # Find all Python files in current directory and subdirectories
            python_files = []
            for root, dirs, files in os.walk('.'):
                for file in files:
                    if file.endswith('.py'):
                        python_files.append(os.path.join(root, file))

            # Check syntax of each Python file
            for file_path in python_files:
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()

                    ast.parse(content)

                except SyntaxError as e:
                    result["valid"] = False
                    result["errors"].append(f"{file_path}: {e}")
                except Exception as e:
                    # Skip files that can't be read
                    continue

        except Exception as e:
            result["errors"].append(f"Syntax validation error: {e}")

        return result

    def _validate_security(self) -> Dict[str, Any]:
        """Perform basic security validation."""
        result = {
            "valid": True,
            "warnings": []
        }

        # This is a placeholder for security validation
        # In a production environment, you might integrate with security tools
        # like bandit for Python, or other static analysis tools

        # For now, we'll just check for obvious security anti-patterns
        security_patterns = [
            r'eval\s*\(',
            r'exec\s*\(',
            r'os\.system\s*\(',
            r'subprocess\.call\s*\([^)]*shell\s*=\s*True',
        ]

        try:
            for root, dirs, files in os.walk('.'):
                for file in files:
                    if file.endswith('.py'):
                        file_path = os.path.join(root, file)
                        try:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                content = f.read()

                            for pattern in security_patterns:
                                if re.search(pattern, content):
                                    result["warnings"].append(
                                        f"{file_path}: Potential security issue detected (pattern: {pattern})"
                                    )
                        except Exception:
                            continue

        except Exception as e:
            result["warnings"].append(f"Security validation error: {e}")

        return result

    def _count_changed_lines(self, original: str, modified: str) -> int:
        """Count the number of lines that were changed."""
        original_lines = original.split('\n')
        modified_lines = modified.split('\n')

        # Simple diff count - could be made more sophisticated
        max_lines = max(len(original_lines), len(modified_lines))
        changed_count = 0

        for i in range(max_lines):
            original_line = original_lines[i] if i < len(
                original_lines) else ""
            modified_line = modified_lines[i] if i < len(
                modified_lines) else ""

            if original_line != modified_line:
                changed_count += 1

        return changed_count

    def get_agent_info(self) -> Dict[str, Any]:
        """Get information about the Code Healer Agent."""
        return {
            "agent_name": "CodeHealerAgent",
            "version": "1.0.0",
            "capabilities": [
                "Apply SonarQube fixes",
                "Syntax validation",
                "Security validation",
                "File backup",
                "Metrics tracking",
                "Multiple fix types (replace, insert, delete, regex)"
            ],
            "supported_languages": ["Python", "Java", "JavaScript", "TypeScript"],
            "validation_enabled": {
                "syntax": self.validate_syntax,
                "security": self.validate_security
            },
            "backup_enabled": self.backup_files
        }
