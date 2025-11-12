"""
Code Healer Agent - Applies actual code fixes based on Bug Hunter Agent suggestions.

This agent receives FixPlan objects from the Bug Hunter Agent and:
1. Reads and analyzes the target code files
2. Generates concrete code fixes using LLM
3. Applies fixes to files with backup and validation
4. Creates Git branches and commits with the changes
5. Generates merge requests for review
"""

import os
import re
import shutil
import subprocess
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import tempfile
from datetime import datetime

from .base_agent import BaseAgent
from ..models import FixPlan, CodeFix, ValidationResult, AgentMetrics
from ..integrations.git_client import GitClient
from ..config import Config


class CodeContext:
    """Context information about the code being fixed."""
    
    def __init__(self, file_path: str, content: str, target_line: int):
        self.file_path = file_path
        self.content = content
        self.target_line = target_line
        self.lines = content.split('\n')
        
    @property
    def target_line_content(self) -> str:
        """Get the content of the target line."""
        if 0 <= self.target_line - 1 < len(self.lines):
            return self.lines[self.target_line - 1]
        return ""
    
    def get_context_around_line(self, context_lines: int = 10) -> str:
        """Get code context around the target line."""
        start = max(0, self.target_line - context_lines - 1)
        end = min(len(self.lines), self.target_line + context_lines)
        
        context_with_numbers = []
        for i in range(start, end):
            line_num = i + 1
            marker = " -> " if line_num == self.target_line else "    "
            context_with_numbers.append(f"{line_num:3d}{marker}{self.lines[i]}")
        
        return '\n'.join(context_with_numbers)


class JavaCodeValidator:
    """Validates Java code syntax and compilation."""
    
    def __init__(self, config: Config):
        self.config = config
        self.temp_dir = tempfile.mkdtemp(prefix="code_healer_")
    
    def validate_syntax(self, java_code: str, file_path: str) -> ValidationResult:
        """Validate Java code syntax by attempting compilation."""
        syntax_errors = []
        linting_errors = []
        security_warnings = []
        
        try:
            # Create temporary file for validation
            temp_file = os.path.join(self.temp_dir, os.path.basename(file_path))
            with open(temp_file, 'w', encoding='utf-8') as f:
                f.write(java_code)
            
            # Try to compile with javac if available
            try:
                result = subprocess.run(
                    ['javac', '-cp', '.', temp_file],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                if result.returncode != 0:
                    syntax_errors.append(f"Compilation failed: {result.stderr}")
                
            except (subprocess.TimeoutExpired, FileNotFoundError):
                # javac not available or timeout, do basic syntax checks
                syntax_errors.extend(self._basic_syntax_check(java_code))
            
            # Basic linting checks
            linting_errors.extend(self._basic_linting_check(java_code))
            
            # Security checks
            security_warnings.extend(self._basic_security_check(java_code))
            
        except Exception as e:
            syntax_errors.append(f"Validation error: {str(e)}")
        
        finally:
            # Cleanup temp file
            if os.path.exists(temp_file):
                os.remove(temp_file)
        
        is_valid = len(syntax_errors) == 0
        confidence = 1.0 if is_valid else max(0.0, 1.0 - len(syntax_errors) * 0.2)
        
        return ValidationResult(
            is_valid=is_valid,
            syntax_errors=syntax_errors,
            linting_errors=linting_errors,
            security_warnings=security_warnings,
            confidence_score=confidence
        )
    
    def _basic_syntax_check(self, java_code: str) -> List[str]:
        """Basic Java syntax validation."""
        errors = []
        
        # Check for balanced braces
        brace_count = java_code.count('{') - java_code.count('}')
        if brace_count != 0:
            errors.append(f"Unbalanced braces: {brace_count} extra opening braces" if brace_count > 0 else f"{-brace_count} extra closing braces")
        
        # Check for balanced parentheses
        paren_count = java_code.count('(') - java_code.count(')')
        if paren_count != 0:
            errors.append(f"Unbalanced parentheses: {paren_count} extra opening" if paren_count > 0 else f"{-paren_count} extra closing")
        
        # Check for basic Java keywords and structure
        if 'class ' in java_code and not re.search(r'class\s+\w+', java_code):
            errors.append("Invalid class declaration syntax")
        
        return errors
    
    def _basic_linting_check(self, java_code: str) -> List[str]:
        """Basic Java linting checks."""
        warnings = []
        
        # Check for unused imports (basic check)
        import_lines = [line for line in java_code.split('\n') if line.strip().startswith('import ')]
        for import_line in import_lines:
            if 'import ' in import_line:
                imported_class = import_line.split('.')[-1].replace(';', '').strip()
                if imported_class not in java_code.replace(import_line, ''):
                    warnings.append(f"Potentially unused import: {import_line.strip()}")
        
        return warnings
    
    def _basic_security_check(self, java_code: str) -> List[str]:
        """Basic security checks."""
        warnings = []
        
        # Check for SQL injection patterns
        if re.search(r'Statement.*executeQuery.*\+', java_code):
            warnings.append("Potential SQL injection: String concatenation in SQL query")
        
        # Check for hardcoded passwords
        if re.search(r'password\s*=\s*["\'][^"\']+["\']', java_code, re.IGNORECASE):
            warnings.append("Potential hardcoded password detected")
        
        return warnings
    
    def cleanup(self):
        """Clean up temporary directory."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)


class BackupManager:
    """Manages file backups before applying fixes."""
    
    def __init__(self, backup_dir: str = "backups"):
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(exist_ok=True)
        
    def create_backup(self, file_path: str) -> str:
        """Create a backup of the file and return backup path."""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Cannot backup non-existent file: {file_path}")
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{os.path.basename(file_path)}.{timestamp}.backup"
        backup_path = self.backup_dir / backup_name
        
        shutil.copy2(file_path, backup_path)
        return str(backup_path)
    
    def restore_backup(self, original_path: str, backup_path: str) -> bool:
        """Restore file from backup."""
        try:
            if os.path.exists(backup_path):
                shutil.copy2(backup_path, original_path)
                return True
            return False
        except Exception:
            return False


class CodeHealerAgent(BaseAgent):
    """Agent that applies code fixes based on Bug Hunter suggestions."""
    
    def __init__(self, config: Config):
        super().__init__(config, "CodeHealerAgent")
        self.git_client = GitClient(config)
        self.java_validator = JavaCodeValidator(config)
        self.backup_manager = BackupManager()
        
        # Configuration
        self.prefer_try_with_resources = True
        self.max_fixes_per_branch = 10
        self.create_backup = True
        self.validate_compilation = False  # Disabled by default for Spring Boot projects
        self.auto_create_mr = True
        self.batch_similar_fixes = True
        self.min_confidence_for_auto_fix = 0.8
    
    def process(self, fix_plans: List[FixPlan]) -> Dict[str, Any]:
        """Main processing method for applying code fixes."""
        self.start_metrics_tracking()
        
        try:
            self.logger.info(f"Starting Code Healer processing", 
                           fix_plans_count=len(fix_plans),
                           session_id=self.session_id)
            
            applied_fixes = []
            created_branches = []
            merge_requests = []
            errors = []
            
            # Group fixes by file or similarity if batching is enabled
            fix_groups = self._group_fixes(fix_plans) if self.batch_similar_fixes else [[fp] for fp in fix_plans]
            
            for group_index, fix_group in enumerate(fix_groups):
                try:
                    self.logger.info(f"Processing fix group {group_index + 1}/{len(fix_groups)}", 
                                   fixes_in_group=len(fix_group))
                    
                    group_fixes = []
                    
                    for fix_plan in fix_group:
                        try:
                            # Process individual fix
                            code_fix = self._process_single_fix(fix_plan)
                            if code_fix and code_fix.is_valid:
                                group_fixes.append(code_fix)
                                applied_fixes.append(code_fix)
                                
                                if self.metrics:
                                    self.metrics.fixes_validated += 1
                            
                        except Exception as e:
                            error_msg = f"Failed to process fix for {fix_plan.issue_key}: {str(e)}"
                            errors.append(error_msg)
                            self.log_error(e, f"Processing fix {fix_plan.issue_key}")
                    
                    # Create Git branch and commit for this group
                    if group_fixes:
                        try:
                            branch_name = self._create_git_branch_and_commit(group_fixes)
                            created_branches.append(branch_name)
                            
                            # Create merge request if enabled
                            if self.auto_create_mr:
                                mr_url = self._create_merge_request(group_fixes, branch_name)
                                if mr_url:
                                    merge_requests.append(mr_url)
                                    
                                    if self.metrics:
                                        self.metrics.merge_requests_created += 1
                        
                        except Exception as e:
                            error_msg = f"Failed to create Git branch for group {group_index + 1}: {str(e)}"
                            errors.append(error_msg)
                            self.log_error(e, f"Git operations for group {group_index + 1}")
                
                except Exception as e:
                    error_msg = f"Failed to process fix group {group_index + 1}: {str(e)}"
                    errors.append(error_msg)
                    self.log_error(e, f"Processing fix group {group_index + 1}")
            
            # Update metrics
            if self.metrics:
                self.metrics.issues_processed = len(fix_plans)
                self.metrics.fixes_generated = len(applied_fixes)
            
            # Prepare results
            results = {
                "session_id": self.session_id,
                "total_fix_plans": len(fix_plans),
                "fixes_applied": len(applied_fixes),
                "fixes_validated": len([f for f in applied_fixes if f.is_valid]),
                "branches_created": len(created_branches),
                "merge_requests_created": len(merge_requests),
                "success_rate": len(applied_fixes) / len(fix_plans) if fix_plans else 0.0,
                "errors": errors,
                "applied_fixes": applied_fixes,
                "created_branches": created_branches,
                "merge_requests": merge_requests
            }
            
            self.logger.info("Code Healer processing completed", **{k: v for k, v in results.items() if k != "applied_fixes"})
            
            return results
            
        except Exception as e:
            self.log_error(e, "Code Healer main processing")
            raise
        
        finally:
            self.stop_metrics_tracking()
            self.java_validator.cleanup()
    
    def _process_single_fix(self, fix_plan: FixPlan) -> Optional[CodeFix]:
        """Process a single fix plan and return the applied fix."""
        try:
            self.logger.info(f"Processing fix for issue {fix_plan.issue_key}", 
                           file_path=fix_plan.file_path,
                           line_number=fix_plan.line_number,
                           confidence=fix_plan.confidence_score)
            
            # Check confidence threshold
            if fix_plan.confidence_score < self.min_confidence_for_auto_fix:
                self.logger.warning(f"Skipping fix due to low confidence", 
                                  issue_key=fix_plan.issue_key,
                                  confidence=fix_plan.confidence_score,
                                  threshold=self.min_confidence_for_auto_fix)
                return None
            
            # Read and analyze code
            context = self._read_and_analyze_code(fix_plan)
            if not context:
                return None
            
            # Generate code fix
            code_fix = self._generate_code_fix(fix_plan, context)
            if not code_fix:
                return None
            
            # Apply fix to file
            if self._apply_fix_to_file(code_fix):
                # Validate the fix
                validation_result = self._validate_fix(code_fix)
                code_fix.validation_status = validation_result.is_valid
                code_fix.validation_errors = validation_result.all_issues
                
                if not validation_result.is_valid:
                    self.logger.warning(f"Fix validation failed for {fix_plan.issue_key}", 
                                      validation_errors=validation_result.all_issues)
                    # Restore backup if validation fails
                    self._restore_from_backup(fix_plan.file_path)
                
                return code_fix
            
            return None
            
        except Exception as e:
            self.log_error(e, f"Processing single fix {fix_plan.issue_key}")
            return None
    
    def _read_and_analyze_code(self, fix_plan: FixPlan) -> Optional[CodeContext]:
        """Read target file and analyze code context."""
        try:
            # Construct full path using the target repository path from config
            full_file_path = os.path.join(self.config.target_repo_path, fix_plan.file_path)
            
            if not os.path.exists(full_file_path):
                self.logger.error(f"File not found: {full_file_path} (relative: {fix_plan.file_path})")
                return None
            
            with open(full_file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            context = CodeContext(full_file_path, content, fix_plan.line_number)
            
            self.logger.debug(f"Read code context for {full_file_path}", 
                            file_size=len(content),
                            total_lines=len(context.lines),
                            target_line=fix_plan.line_number)
            
            return context
            
        except Exception as e:
            self.log_error(e, f"Reading code context for {fix_plan.file_path}")
            return None
    
    def _generate_code_fix(self, fix_plan: FixPlan, context: CodeContext) -> Optional[CodeFix]:
        """Generate actual code fix using LLM."""
        try:
            # Create specialized prompt for Java code fixing
            system_prompt = self._create_system_prompt()
            user_prompt = self._create_user_prompt(fix_plan, context)
            
            # Generate fix using LLM
            fixed_code_section = self.generate_response(
                prompt=user_prompt,
                system_prompt=system_prompt,
                temperature=0.3,  # Lower temperature for more deterministic code fixes
                max_tokens=4096
            )
            
            # Extract the fixed code from the response
            fixed_code = self._extract_fixed_code(fixed_code_section, context)
            if not fixed_code:
                self.logger.error(f"Could not extract valid fixed code for {fix_plan.issue_key}")
                return None
            
            # Generate diff
            diff = self._generate_diff(context.content, fixed_code)
            
            # Create branch name and commit message
            branch_name = self._generate_branch_name(fix_plan)
            commit_message = self._generate_commit_message(fix_plan)
            
            code_fix = CodeFix(
                fix_plan=fix_plan,
                original_code=context.content,
                fixed_code=fixed_code,
                diff=diff,
                validation_status=False,  # Will be set during validation
                validation_errors=[],
                branch_name=branch_name,
                commit_message=commit_message
            )
            
            self.logger.info(f"Generated code fix for {fix_plan.issue_key}", 
                           original_size=len(context.content),
                           fixed_size=len(fixed_code),
                           diff_lines=len(diff.split('\n')))
            
            return code_fix
            
        except Exception as e:
            self.log_error(e, f"Generating code fix for {fix_plan.issue_key}")
            return None
    
    def _create_system_prompt(self) -> str:
        """Create system prompt for LLM code fixing."""
        return """You are an expert Java developer specializing in fixing resource leak issues in Spring Boot applications.

Your task is to generate precise code fixes that:
1. Follow Java best practices and Spring Boot conventions
2. Properly handle resource management (Connections, Statements, ResultSets)
3. Maintain existing functionality while fixing the resource leak
4. Use appropriate patterns (try-with-resources or finally blocks)
5. Include proper error handling and logging

IMPORTANT INSTRUCTIONS:
- Generate ONLY the complete fixed file content
- Maintain the same class structure, imports, and method signatures
- Do not add explanatory text or comments about the fix
- Ensure the code compiles and runs correctly
- Use try-with-resources pattern when possible for resource management
- Add proper exception handling where needed"""
    
    def _create_user_prompt(self, fix_plan: FixPlan, context: CodeContext) -> str:
        """Create user prompt for specific fix."""
        return f"""Fix this resource leak issue in Java code:

**Issue**: {fix_plan.issue_description}
**File**: {fix_plan.file_path}:{fix_plan.line_number}
**Problem**: {fix_plan.problem_analysis}
**Solution Strategy**: {fix_plan.proposed_solution}

**Current Code Context** (around line {fix_plan.line_number}):
```java
{context.get_context_around_line(15)}
```

**Target Line** (line {fix_plan.line_number}):
```java
{context.target_line_content}
```

**Complete File Content**:
```java
{context.content}
```

Please provide the complete fixed file content that resolves the resource leak while maintaining all existing functionality."""
    
    def _extract_fixed_code(self, llm_response: str, context: CodeContext) -> Optional[str]:
        """Extract fixed code from LLM response."""
        try:
            # Look for code blocks in the response
            code_blocks = re.findall(r'```java\n(.*?)\n```', llm_response, re.DOTALL)
            
            if code_blocks:
                # Use the largest code block (likely the complete file)
                fixed_code = max(code_blocks, key=len).strip()
            else:
                # If no code blocks, try to extract the entire response as code
                fixed_code = llm_response.strip()
            
            # Basic validation - should contain class declaration if original did
            if 'class ' in context.content and 'class ' not in fixed_code:
                self.logger.warning("Fixed code missing class declaration")
                return None
            
            return fixed_code
            
        except Exception as e:
            self.logger.error(f"Error extracting fixed code: {str(e)}")
            return None
    
    def _generate_diff(self, original: str, fixed: str) -> str:
        """Generate a simple diff between original and fixed code."""
        try:
            import difflib
            
            original_lines = original.splitlines(keepends=True)
            fixed_lines = fixed.splitlines(keepends=True)
            
            diff = ''.join(difflib.unified_diff(
                original_lines,
                fixed_lines,
                fromfile='original',
                tofile='fixed',
                lineterm=''
            ))
            
            return diff
            
        except Exception:
            return f"Original: {len(original)} chars\nFixed: {len(fixed)} chars"
    
    def _apply_fix_to_file(self, code_fix: CodeFix) -> bool:
        """Apply the generated fix to the actual file."""
        try:
            # Use the full file path from the code context
            file_path = code_fix.fix_plan.file_path
            full_file_path = os.path.join(self.config.target_repo_path, file_path)
            
            # Create backup if enabled
            backup_path = None
            if self.create_backup:
                backup_path = self.backup_manager.create_backup(full_file_path)
                self.logger.info(f"Created backup for {full_file_path}", backup_path=backup_path)
            
            # Write fixed code to file
            with open(full_file_path, 'w', encoding='utf-8') as f:
                f.write(code_fix.fixed_code)
            
            self.logger.info(f"Applied fix to {full_file_path}", 
                           issue_key=code_fix.fix_plan.issue_key,
                           backup_created=backup_path is not None)
            
            return True
            
        except Exception as e:
            self.log_error(e, f"Applying fix to {code_fix.fix_plan.file_path}")
            return False
    
    def _validate_fix(self, code_fix: CodeFix) -> ValidationResult:
        """Validate the applied fix."""
        try:
            if self.validate_compilation:
                return self.java_validator.validate_syntax(
                    code_fix.fixed_code,
                    code_fix.fix_plan.file_path
                )
            else:
                # Basic validation without compilation
                return ValidationResult(
                    is_valid=True,
                    syntax_errors=[],
                    linting_errors=[],
                    security_warnings=[],
                    confidence_score=0.8
                )
                
        except Exception as e:
            self.log_error(e, f"Validating fix for {code_fix.fix_plan.issue_key}")
            return ValidationResult(
                is_valid=False,
                syntax_errors=[f"Validation error: {str(e)}"],
                linting_errors=[],
                security_warnings=[],
                confidence_score=0.0
            )
    
    def _restore_from_backup(self, file_path: str) -> bool:
        """Restore file from backup."""
        try:
            # Use full file path
            full_file_path = os.path.join(self.config.target_repo_path, file_path)
            
            # Find the most recent backup for this file
            backup_files = list(self.backup_manager.backup_dir.glob(f"{os.path.basename(file_path)}.*.backup"))
            if backup_files:
                latest_backup = max(backup_files, key=os.path.getctime)
                success = self.backup_manager.restore_backup(full_file_path, str(latest_backup))
                if success:
                    self.logger.info(f"Restored {full_file_path} from backup", backup_file=str(latest_backup))
                return success
            return False
            
        except Exception as e:
            self.log_error(e, f"Restoring backup for {file_path}")
            return False
    
    def _group_fixes(self, fix_plans: List[FixPlan]) -> List[List[FixPlan]]:
        """Group fixes for batching."""
        if not self.batch_similar_fixes:
            return [[fp] for fp in fix_plans]
        
        # Group by file path
        file_groups = {}
        for fix_plan in fix_plans:
            file_path = fix_plan.file_path
            if file_path not in file_groups:
                file_groups[file_path] = []
            file_groups[file_path].append(fix_plan)
        
        # Split large groups
        groups = []
        for file_fixes in file_groups.values():
            if len(file_fixes) <= self.max_fixes_per_branch:
                groups.append(file_fixes)
            else:
                # Split into smaller groups
                for i in range(0, len(file_fixes), self.max_fixes_per_branch):
                    groups.append(file_fixes[i:i + self.max_fixes_per_branch])
        
        return groups
    
    def _generate_branch_name(self, fix_plan: FixPlan) -> str:
        """Generate Git branch name for fix."""
        issue_key_short = fix_plan.issue_key[:8] if len(fix_plan.issue_key) > 8 else fix_plan.issue_key
        file_name = os.path.basename(fix_plan.file_path).replace('.java', '')
        return f"fix/sonar-{issue_key_short}-{file_name}-resource-leak"
    
    def _generate_commit_message(self, fix_plan: FixPlan) -> str:
        """Generate Git commit message for fix."""
        return f"""fix(sonar): resolve resource leak in {os.path.basename(fix_plan.file_path)}

- Issue: {fix_plan.issue_key}
- Type: Resource Leak
- File: {fix_plan.file_path}:{fix_plan.line_number}
- Fix: {fix_plan.proposed_solution[:100]}...
- Confidence: {fix_plan.confidence_score:.2f}

Resolves SonarQube issue: {fix_plan.issue_key}"""
    
    def _create_git_branch_and_commit(self, fixes: List[CodeFix]) -> str:
        """Create Git branch and commit changes."""
        try:
            # Use the first fix's branch name, or create a batch name
            if len(fixes) == 1:
                branch_name = fixes[0].branch_name
                commit_message = fixes[0].commit_message
            else:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                branch_name = f"fix/sonar-batch-{timestamp}-resource-leaks"
                commit_message = f"fix(sonar): resolve {len(fixes)} resource leak issues\n\n" + \
                               "\n".join([f"- {fix.fix_plan.issue_key}: {os.path.basename(fix.fix_plan.file_path)}" 
                                        for fix in fixes])
            
            # Create and checkout branch
            if not self.git_client.create_branch(branch_name):
                raise Exception(f"Failed to create branch: {branch_name}")
            
            # Commit all modified files (use relative paths for git)
            modified_files = [fix.fix_plan.file_path for fix in fixes]
            if not self.git_client.commit_changes(modified_files, commit_message):
                raise Exception(f"Failed to commit changes to branch: {branch_name}")
            
            # Push branch to remote repository
            if not self.git_client.push_branch(branch_name):
                self.logger.warning(f"Failed to push branch to remote: {branch_name}")
                # Don't fail the entire operation if push fails - branch still exists locally
            else:
                self.logger.info(f"Successfully pushed branch to remote: {branch_name}")
            
            self.logger.info(f"Created Git branch and committed changes", 
                           branch_name=branch_name,
                           files_committed=len(fixes),
                           pushed_to_remote=True)
            
            return branch_name
            
        except Exception as e:
            self.log_error(e, "Creating Git branch and commit")
            raise
    
    def _create_merge_request(self, fixes: List[CodeFix], branch_name: str) -> Optional[str]:
        """Create merge request for the fixes."""
        try:
            # Generate MR title and description
            if len(fixes) == 1:
                fix = fixes[0]
                title = f"Fix SonarQube issue: {fix.fix_plan.issue_key}"
                description = self._generate_mr_description(fix)
            else:
                title = f"Fix {len(fixes)} SonarQube resource leak issues"
                description = self._generate_batch_mr_description(fixes)
            
            # Generate proper GitHub pull request URL
            # Extract repository info from target repo URL
            repo_url = self.config.target_repo_url
            if repo_url and "github.com" in repo_url:
                # Extract owner/repo from GitHub URL
                # e.g., https://github.com/naveenvivek/SpringBootAppSonarAI -> naveenvivek/SpringBootAppSonarAI
                repo_path = repo_url.replace("https://github.com/", "").replace(".git", "")
                mr_url = f"https://github.com/{repo_path}/compare/{self.config.target_repo_branch}...{branch_name}?expand=1"
            else:
                # Fallback for non-GitHub repositories
                mr_url = f"Pull request ready for branch: {branch_name}"
            
            self.logger.info(f"Merge request ready for creation", 
                           branch_name=branch_name,
                           title=title,
                           description_length=len(description),
                           fixes_count=len(fixes),
                           pull_request_url=mr_url)
            
            return mr_url
            
        except Exception as e:
            self.log_error(e, f"Creating merge request for branch {branch_name}")
            return None
    
    def _generate_mr_description(self, fix: CodeFix) -> str:
        """Generate merge request description for single fix."""
        return f"""## SonarQube Issue Fix

**Issue ID**: {fix.fix_plan.issue_key}
**Severity**: Resource Leak
**Confidence**: {fix.fix_plan.confidence_score:.2f}

### Problem
{fix.fix_plan.problem_analysis}

### Solution
{fix.fix_plan.proposed_solution}

### Files Changed
- `{fix.fix_plan.file_path}` (line {fix.fix_plan.line_number})

### Code Changes
```diff
{fix.diff}
```

### Validation
- [{'x' if fix.validation_status else ' '}] Code compiles successfully
- [{'x' if fix.validation_status else ' '}] Functionality preserved
- [{'x' if fix.validation_status else ' '}] Resource leak resolved
- [x] Best practices followed

### Side Effects
{', '.join(fix.fix_plan.potential_side_effects) if fix.fix_plan.potential_side_effects else 'None identified'}

### Testing
- Manual testing performed: Recommended
- Unit tests updated: Not required for this fix
- Integration tests passed: Recommended to verify"""
    
    def _generate_batch_mr_description(self, fixes: List[CodeFix]) -> str:
        """Generate merge request description for batch fixes."""
        files_changed = [f"- `{fix.fix_plan.file_path}` (line {fix.fix_plan.line_number})" for fix in fixes]
        
        return f"""## SonarQube Batch Fix: Resource Leaks

**Issues Fixed**: {len(fixes)}
**Type**: Resource Leak Resolution
**Average Confidence**: {sum(fix.fix_plan.confidence_score for fix in fixes) / len(fixes):.2f}

### Problems Resolved
This batch fix resolves multiple resource leak issues identified by SonarQube analysis.

### Files Changed
{chr(10).join(files_changed)}

### Validation Summary
- Fixes applied: {len(fixes)}
- Validation passed: {len([f for f in fixes if f.validation_status])}
- Compilation successful: {len([f for f in fixes if f.validation_status])}

### Issue Details
{chr(10).join([f"- **{fix.fix_plan.issue_key}**: {fix.fix_plan.proposed_solution[:100]}..." for fix in fixes])}

### Testing
- Manual testing recommended for all modified files
- Integration tests should be run to verify functionality
- No unit test updates required for these fixes"""