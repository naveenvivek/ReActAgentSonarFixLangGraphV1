"""
LangGraph workflow for Code Healer Agent.
Implements nodes and edges for applying SonarQube fixes with single branch atomic strategy.
"""

from typing import Dict, List, Any, Optional, TypedDict
from datetime import datetime
import json
import time
from langgraph.graph import StateGraph, END
import logging

from ..agents.code_healer_agent import CodeHealerAgent
from ..models import FixPlan
from ..config import Config
from ..utils.logger import get_logger
from ..utils.fixplan_storage import FixPlanStorage
from ..integrations.gitlab_client import GitLabClient


class CodeHealerWorkflowState(TypedDict):
    """State for Code Healer workflow."""
    # Input parameters
    project_key: Optional[str]
    fix_plans: List[FixPlan]

    # Git workflow data
    branch_name: Optional[str]
    applied_fixes: List[Dict[str, Any]]
    failed_fixes: List[Dict[str, Any]]

    # Build validation data
    build_status: Optional[str]
    build_output: Optional[str]
    build_errors: List[str]

    # Status and metadata
    workflow_status: str  # 'running', 'completed', 'error'
    error_message: Optional[str]
    current_fix_index: int
    total_fixes: int

    # Session tracking
    session_id: Optional[str]

    # Results
    results: Dict[str, Any]


class CodeHealerWorkflow:
    """LangGraph workflow for Code Healer Agent with single branch atomic fixes."""

    def __init__(self, config: Config):
        """Initialize Code Healer workflow."""
        self.config = config
        self.agent = CodeHealerAgent(config)

        # Initialize file-based logger
        self.logger = get_logger(config, "sonar_ai_agent.code_healer_workflow")

        # Initialize fix plan storage and Git client
        self.fix_plan_storage = FixPlanStorage()
        self.git_client = GitLabClient(config)

        # Build the workflow graph
        self.workflow = self._build_workflow()

    def _build_workflow(self) -> StateGraph:
        """Build the LangGraph workflow with nodes and edges."""
        workflow = StateGraph(CodeHealerWorkflowState)

        # Add nodes
        workflow.add_node("initialize", self._initialize_node)
        workflow.add_node("validate_fix_plans", self._validate_fix_plans_node)
        workflow.add_node("create_branch", self._create_branch_node)
        workflow.add_node("apply_fixes", self._apply_fixes_node)
        workflow.add_node("validate_changes", self._validate_changes_node)
        workflow.add_node("maven_clean_build", self._build_validation_node)
        workflow.add_node("commit_and_push", self._commit_and_push_node)
        workflow.add_node("create_merge_request",
                          self._create_merge_request_node)
        workflow.add_node("finalize", self._finalize_node)
        workflow.add_node("handle_error", self._handle_error_node)

        # Set entry point
        workflow.set_entry_point("initialize")

        # Add edges
        workflow.add_edge("initialize", "validate_fix_plans")

        workflow.add_conditional_edges(
            "validate_fix_plans",
            self._check_for_errors,
            {"continue": "create_branch", "error": "handle_error"}
        )

        workflow.add_conditional_edges(
            "create_branch",
            self._check_for_errors,
            {"continue": "apply_fixes", "error": "handle_error"}
        )

        workflow.add_conditional_edges(
            "apply_fixes",
            self._check_for_errors,
            {"continue": "validate_changes", "error": "handle_error"}
        )

        workflow.add_conditional_edges(
            "validate_changes",
            self._check_for_errors,
            {"continue": "maven_clean_build", "error": "handle_error"}
        )

        workflow.add_conditional_edges(
            "maven_clean_build",
            self._check_for_errors,
            {"continue": "commit_and_push", "error": "handle_error"}
        )

        workflow.add_conditional_edges(
            "commit_and_push",
            self._check_for_errors,
            {"continue": "create_merge_request", "error": "handle_error"}
        )

        workflow.add_edge("create_merge_request", "finalize")
        workflow.add_edge("finalize", END)
        workflow.add_edge("handle_error", END)

        return workflow.compile(checkpointer=None, debug=False)

    def _initialize_node(self, state: CodeHealerWorkflowState) -> CodeHealerWorkflowState:
        """Initialize the Code Healer workflow."""
        self.logger.info("🩹 Initializing Code Healer workflow")

        # Start metrics tracking
        self.agent.start_metrics_tracking()

        # Initialize session
        session_id = f"code_healer_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # Update state
        state.update({
            "workflow_status": "running",
            "error_message": None,
            "applied_fixes": [],
            "failed_fixes": [],
            "current_fix_index": 0,
            "total_fixes": len(state.get("fix_plans", [])),
            "branch_name": None,
            "session_id": session_id,
            "results": {}
        })

        self.logger.info(
            f"✅ Code Healer workflow initialized with session: {session_id}")
        return state

    def _validate_fix_plans_node(self, state: CodeHealerWorkflowState) -> CodeHealerWorkflowState:
        """Validate input fix plans."""
        self.logger.info("📋 Validating fix plans")

        fix_plans = state.get("fix_plans", [])

        if not fix_plans:
            state["error_message"] = "No fix plans provided for Code Healer"
            state["workflow_status"] = "error"
            self.logger.error("❌ No fix plans provided")
            return state

        # Validate each fix plan
        valid_plans = []
        invalid_plans = []

        for plan in fix_plans:
            if self._is_valid_fix_plan(plan):
                valid_plans.append(plan)
            else:
                invalid_plans.append(plan)

        if not valid_plans:
            state["error_message"] = "No valid fix plans found"
            state["workflow_status"] = "error"
            self.logger.error("❌ No valid fix plans found")
            return state

        state["fix_plans"] = valid_plans
        state["total_fixes"] = len(valid_plans)

        self.logger.info(
            f"✅ Validated {len(valid_plans)} fix plans (skipped {len(invalid_plans)} invalid)")
        return state

    def _create_branch_node(self, state: CodeHealerWorkflowState) -> CodeHealerWorkflowState:
        """Create single branch for atomic fixes."""
        self.logger.info("🌿 Creating branch for atomic fixes")

        try:
            # Generate timestamp-based branch name
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            branch_name = f"sonar-ai-fixes-{timestamp}"

            # Create branch from main
            success = self.git_client.create_branch(branch_name)
            if not success:
                state["error_message"] = f"Failed to create branch: {branch_name}"
                state["workflow_status"] = "error"
                return state

            state["branch_name"] = branch_name
            self.logger.info(f"✅ Created branch: {branch_name}")

        except Exception as e:
            state["error_message"] = f"Branch creation failed: {str(e)}"
            state["workflow_status"] = "error"
            self.logger.error(f"❌ Branch creation failed: {e}")

        return state

    def _apply_fixes_node(self, state: CodeHealerWorkflowState) -> CodeHealerWorkflowState:
        """Apply all fixes atomically to the branch."""
        fix_plans = state["fix_plans"]
        self.logger.info(f"🔧 Applying {len(fix_plans)} fixes atomically")

        applied_fixes = []
        failed_fixes = []

        for i, fix_plan in enumerate(fix_plans):
            try:
                self.logger.info(
                    f"⚡ Applying fix {i+1}/{len(fix_plans)}: {fix_plan.issue_key}")

                # Apply individual fix
                result = self.agent.apply_fix(fix_plan)

                if result["success"]:
                    applied_fixes.append({
                        "fix_plan": fix_plan,
                        "result": result,
                        "status": "applied"
                    })
                    self.logger.info(
                        f"✅ Successfully applied fix: {fix_plan.issue_key}")
                else:
                    failed_fixes.append({
                        "fix_plan": fix_plan,
                        "error": result.get("error", "Unknown error"),
                        "status": "failed"
                    })
                    self.logger.warning(
                        f"⚠️ Failed to apply fix: {fix_plan.issue_key}")

            except Exception as e:
                failed_fixes.append({
                    "fix_plan": fix_plan,
                    "error": str(e),
                    "status": "failed"
                })
                self.logger.error(
                    f"❌ Exception applying fix {fix_plan.issue_key}: {e}")

        state["applied_fixes"] = applied_fixes
        state["failed_fixes"] = failed_fixes

        # Check if any fixes were applied successfully
        if not applied_fixes:
            state["error_message"] = "No fixes were applied successfully"
            state["workflow_status"] = "error"

        self.logger.info(
            f"📊 Fix application complete: {len(applied_fixes)} successful, {len(failed_fixes)} failed")
        return state

    def _validate_changes_node(self, state: CodeHealerWorkflowState) -> CodeHealerWorkflowState:
        """Validate applied changes for syntax and security."""
        self.logger.info("🔍 Validating applied changes")

        try:
            # Validate syntax and security of changes
            validation_result = self.agent.validate_changes()

            if not validation_result["valid"]:
                state["error_message"] = f"Validation failed: {validation_result.get('errors', [])}"
                state["workflow_status"] = "error"
                self.logger.error(
                    f"❌ Validation failed: {validation_result.get('errors')}")
                return state

            self.logger.info("✅ All changes validated successfully")

        except Exception as e:
            state["error_message"] = f"Validation error: {str(e)}"
            state["workflow_status"] = "error"
            self.logger.error(f"❌ Validation error: {e}")

        return state

    def _build_validation_node(self, state: CodeHealerWorkflowState) -> CodeHealerWorkflowState:
        """Run build validation to check if fixes break the build (continues on failure with warning)."""
        # Check if Maven build validation is disabled
        if not getattr(self.config, 'enable_maven_build_validation', False):
            self.logger.info(
                "🔓 Maven build validation disabled - skipping build and proceeding to commit")
            state["build_status"] = "skipped"
            state["build_output"] = "Maven build validation disabled by configuration"
            state["build_errors"] = []
            return state

        self.logger.info("🔨 Running Maven clean build")

        try:
            import subprocess
            import os

            # Change to the repository directory
            repo_path = getattr(self.config, 'git_repo_path', os.getcwd())
            original_cwd = os.getcwd()

            # Detect project type and build tool
            project_type = None
            build_command = None

            try:
                os.chdir(repo_path)
                self.logger.info(f"📁 Changed directory to: {repo_path}")

                # Check what type of project this is
                if os.path.exists('pom.xml'):
                    project_type = 'maven'
                    build_command = ['mvn', 'clean', 'install']
                elif os.path.exists('build.gradle') or os.path.exists('build.gradle.kts'):
                    project_type = 'gradle'
                    if os.path.exists('gradlew'):
                        build_command = ['./gradlew', 'clean', 'build']
                    else:
                        build_command = ['gradle', 'clean', 'build']
                elif os.path.exists('package.json'):
                    project_type = 'npm'
                    build_command = ['npm', 'run', 'build']
                elif os.path.exists('requirements.txt') or os.path.exists('setup.py'):
                    project_type = 'python'
                    # For Python, we can run syntax validation instead
                    self.logger.info(
                        "🐍 Python project detected, skipping build validation (syntax already validated)")
                    state["build_status"] = "skipped"
                    state["build_output"] = "Python project - syntax validation already performed"
                    state["build_errors"] = []
                    return state
                else:
                    self.logger.info(
                        "❓ Unknown project type, skipping build validation")
                    state["build_status"] = "skipped"
                    state["build_output"] = "Unknown project type - build validation skipped"
                    state["build_errors"] = []
                    return state

                self.logger.info(
                    f"🏗️ {project_type.title()} project detected, executing: {' '.join(build_command)}")

                # Check if build tool is available
                try:
                    # For Windows, try with .cmd extension as well
                    cmd_variants = [build_command[0]]
                    if os.name == 'nt' and not build_command[0].endswith('.cmd'):
                        cmd_variants.append(build_command[0] + '.cmd')

                    tool_found = False
                    working_cmd = None

                    for cmd_variant in cmd_variants:
                        try:
                            result = subprocess.run([cmd_variant, '--version'],
                                                    capture_output=True, timeout=10, shell=True)
                            if result.returncode == 0:
                                tool_found = True
                                working_cmd = cmd_variant
                                # Update the command
                                build_command[0] = cmd_variant
                                break
                        except (FileNotFoundError, subprocess.TimeoutExpired):
                            continue

                    if not tool_found:
                        warning_msg = f"{build_command[0]} not found in PATH. Skipping build validation."
                        self.logger.warning(f"⚠️ {warning_msg}")
                        state["build_status"] = "skipped"
                        state["build_output"] = warning_msg
                        state["build_errors"] = []
                        return state
                    else:
                        self.logger.info(f"✅ Found {working_cmd}")

                except Exception as e:
                    warning_msg = f"Error checking build tool availability: {str(e)}. Skipping build validation."
                    self.logger.warning(f"⚠️ {warning_msg}")
                    state["build_status"] = "skipped"
                    state["build_output"] = warning_msg
                    state["build_errors"] = []
                    return state                # Run the build command
                result = subprocess.run(
                    build_command,
                    capture_output=True,
                    text=True,
                    timeout=300,  # 5 minute timeout
                    shell=True   # Use shell to help with PATH resolution on Windows
                )

                # Store build results in state
                state["build_status"] = "success" if result.returncode == 0 else "failed"
                state["build_output"] = result.stdout
                state["build_errors"] = result.stderr.split(
                    '\n') if result.stderr else []

                if result.returncode == 0:
                    self.logger.info(
                        f"✅ {project_type.title()} build validation passed successfully")
                else:
                    # Log detailed build output for debugging
                    self.logger.warning(
                        f"⚠️ {project_type.title()} build validation failed with exit code: {result.returncode}")

                    # Always log the full error output for debugging
                    if result.stderr:
                        self.logger.error("📋 Full Maven stderr output:")
                        # Last 20 lines
                        for line in result.stderr.strip().split('\n')[-20:]:
                            self.logger.error(f"   {line}")

                    if result.stdout:
                        self.logger.info("📋 Last 10 lines of Maven stdout:")
                        # Last 10 lines
                        for line in result.stdout.strip().split('\n')[-10:]:
                            self.logger.info(f"   {line}")

                    # Build validation enabled and failed - STOP workflow
                    error_msg = f"{project_type.title()} build validation failed - stopping workflow to prevent committing broken code"
                    self.logger.error(f"❌ {error_msg}")
                    self.logger.error(
                        "🔒 ENABLE_MAVEN_BUILD_VALIDATION=true - workflow stopped on build failure")
                    state["build_status"] = "failed"
                    state["error_message"] = error_msg
                    state["workflow_status"] = "error"

            finally:
                # Always change back to original directory
                os.chdir(original_cwd)

        except subprocess.TimeoutExpired:
            error_msg = f"{project_type.title()} build timed out after 5 minutes"
            self.logger.error(f"❌ {error_msg}")
            state["error_message"] = error_msg
            state["workflow_status"] = "error"
            state["build_status"] = "timeout"
            state["build_errors"] = [error_msg]

        except Exception as e:
            error_msg = f"Build validation error: {str(e)}"
            self.logger.error(f"❌ {error_msg}")
            state["error_message"] = error_msg
            state["workflow_status"] = "error"
            state["build_status"] = "error"
            state["build_errors"] = [str(e)]

        return state

    def _commit_and_push_node(self, state: CodeHealerWorkflowState) -> CodeHealerWorkflowState:
        """Commit all changes atomically and push to remote."""
        self.logger.info("💾 Committing and pushing atomic changes")

        try:
            branch_name = state["branch_name"]
            applied_fixes = state["applied_fixes"]

            # Create comprehensive commit message
            commit_message = self._create_atomic_commit_message(applied_fixes)

            # Commit all changes
            commit_success = self.git_client.commit_changes(commit_message)
            if not commit_success:
                state["error_message"] = "Failed to commit changes"
                state["workflow_status"] = "error"
                return state

            # Push branch to remote
            push_success = self.git_client.push_branch(branch_name)
            if not push_success:
                state["error_message"] = "Failed to push branch"
                state["workflow_status"] = "error"
                return state

            self.logger.info(
                f"✅ Successfully committed and pushed {len(applied_fixes)} fixes to {branch_name}")

        except Exception as e:
            state["error_message"] = f"Commit/push failed: {str(e)}"
            state["workflow_status"] = "error"
            self.logger.error(f"❌ Commit/push failed: {e}")

        return state

    def _create_merge_request_node(self, state: CodeHealerWorkflowState) -> CodeHealerWorkflowState:
        """Create comprehensive merge request for all fixes."""
        self.logger.info("🔀 Creating merge request")

        try:
            branch_name = state["branch_name"]
            applied_fixes = state["applied_fixes"]

            # Create MR title and description
            title = f"🤖 SonarQube AI Fixes - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            description = self._create_mr_description(
                applied_fixes, state["failed_fixes"])

            # Create merge request
            mr_url = self.git_client.create_merge_request(
                source_branch=branch_name,
                target_branch="main",
                title=title,
                description=description
            )

            if mr_url:
                self.logger.info(f"✅ Merge request created: {mr_url}")
                state["results"]["merge_request_url"] = mr_url
            else:
                self.logger.warning(
                    "⚠️ Merge request creation returned no URL")

        except Exception as e:
            # Don't fail the workflow if MR creation fails
            self.logger.warning(f"⚠️ Merge request creation failed: {e}")
            state["results"]["merge_request_error"] = str(e)

        return state

    def _finalize_node(self, state: CodeHealerWorkflowState) -> CodeHealerWorkflowState:
        """Finalize the Code Healer workflow."""
        self.logger.info("🏁 Finalizing Code Healer workflow")

        # Stop metrics tracking
        metrics = self.agent.stop_metrics_tracking()

        # Create final results
        applied_count = len(state["applied_fixes"])
        failed_count = len(state["failed_fixes"])
        total_count = applied_count + failed_count

        results = {
            "status": "success",
            "message": f"Applied {applied_count}/{total_count} fixes successfully",
            "fixes_applied": applied_count,
            "fixes_failed": failed_count,
            "total_fixes": total_count,
            "branch_name": state["branch_name"],
            "processing_time": metrics.processing_time_seconds if metrics else 0,
            "agent": "CodeHealerAgent",
            "timestamp": datetime.now().isoformat(),
            "applied_fixes": [fix["fix_plan"].issue_key for fix in state["applied_fixes"]],
            "failed_fixes": [fix["fix_plan"].issue_key for fix in state["failed_fixes"]]
        }

        # Add MR URL if available
        if "merge_request_url" in state["results"]:
            results["merge_request_url"] = state["results"]["merge_request_url"]

        state["results"] = results
        state["workflow_status"] = "completed"

        # Final workflow summary
        success_rate = applied_count / total_count if total_count > 0 else 1.0

        self.logger.info("Code Healer workflow completed",
                         fixes_applied=applied_count,
                         fixes_failed=failed_count,
                         success_rate=success_rate,
                         branch_name=state["branch_name"],
                         processing_time_seconds=metrics.processing_time_seconds if metrics else 0,
                         session_id=state.get("session_id"))

        self.logger.info(
            f"✅ Code Healer completed: {applied_count}/{total_count} fixes applied")
        return state

    def _handle_error_node(self, state: CodeHealerWorkflowState) -> CodeHealerWorkflowState:
        """Handle workflow errors."""
        error_msg = state.get("error_message", "Unknown error")
        self.logger.error(f"❌ Code Healer workflow error: {error_msg}")

        # Stop metrics tracking
        self.agent.stop_metrics_tracking()

        # Create error results
        state["results"] = {
            "status": "error",
            "message": error_msg,
            "fixes_applied": len(state.get("applied_fixes", [])),
            "fixes_failed": len(state.get("failed_fixes", [])),
            "agent": "CodeHealerAgent",
            "timestamp": datetime.now().isoformat()
        }

        return state

    def _check_for_errors(self, state: CodeHealerWorkflowState) -> str:
        """Check if there are errors in the current state."""
        if state["workflow_status"] == "error":
            return "error"

        # If Maven validation is enabled, check build status to prevent committing broken code
        if getattr(self.config, 'enable_maven_build_validation', False) and state.get("build_status") == "failed":
            self.logger.error(
                "❌ Build validation failed - cannot proceed to commit")
            return "error"

        return "continue"

    def _is_valid_fix_plan(self, fix_plan: FixPlan) -> bool:
        """Validate individual fix plan."""
        return (
            fix_plan.issue_key and
            fix_plan.file_path and
            fix_plan.proposed_solution and
            fix_plan.confidence_score > 0.5
        )

    def _create_atomic_commit_message(self, applied_fixes: List[Dict[str, Any]]) -> str:
        """Create comprehensive commit message for atomic fixes."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        message = f"🔧 SonarQube AI Fixes - {timestamp}\n\n"
        message += f"Applied {len(applied_fixes)} automated fixes to improve code quality:\n\n"

        # Group by severity
        severity_groups = {}
        for fix_data in applied_fixes:
            fix_plan = fix_data["fix_plan"]
            severity = getattr(fix_plan, 'severity', 'UNKNOWN')
            if severity not in severity_groups:
                severity_groups[severity] = []
            severity_groups[severity].append(fix_plan)

        # Add fixes by severity
        severity_icons = {
            'BLOCKER': '🚫',
            'CRITICAL': '⚠️',
            'MAJOR': '📊',
            'MINOR': '📝',
            'INFO': 'ℹ️'
        }

        for severity, fixes in severity_groups.items():
            icon = severity_icons.get(severity, '🔧')
            message += f"{icon} {severity} Issues:\n"
            for fix in fixes:
                message += f"✅ {fix.issue_description[:60]}... ({fix.file_path}:{fix.line_number})\n"
            message += "\n"

        # Add metadata
        total_confidence = sum(
            fix["fix_plan"].confidence_score for fix in applied_fixes)
        avg_confidence = total_confidence / \
            len(applied_fixes) if applied_fixes else 0

        message += f"🤖 Generated by: SonarQube AI Agent v1.0\n"
        message += f"📈 Confidence Score: Average {avg_confidence:.2f}/1.0\n"
        message += f"🎯 Session: {datetime.now().strftime('code_healer_%Y%m%d_%H%M%S')}\n"
        message += f"📊 Total Issues Fixed: {len(applied_fixes)}"

        return message

    def _create_mr_description(self, applied_fixes: List[Dict[str, Any]], failed_fixes: List[Dict[str, Any]]) -> str:
        """Create comprehensive merge request description."""
        description = "# 🤖 SonarQube AI Fixes\n\n"

        # Summary
        total_fixes = len(applied_fixes) + len(failed_fixes)
        description += "## 📊 Summary\n"
        description += f"- **Fixes Applied**: {len(applied_fixes)}/{total_fixes}\n"
        description += f"- **Success Rate**: {len(applied_fixes)/total_fixes*100:.1f}%\n"

        if applied_fixes:
            files_modified = set(
                fix["fix_plan"].file_path for fix in applied_fixes)
            description += f"- **Files Modified**: {len(files_modified)}\n"

            avg_confidence = sum(
                fix["fix_plan"].confidence_score for fix in applied_fixes) / len(applied_fixes)
            description += f"- **Confidence**: High (avg {avg_confidence:.2f}/1.0)\n\n"

        # Applied fixes
        if applied_fixes:
            description += "## ✅ Fixes Applied\n\n"
            for fix_data in applied_fixes:
                fix = fix_data["fix_plan"]
                description += f"### {getattr(fix, 'severity', 'UNKNOWN')} - {fix.issue_key}\n"
                description += f"**File**: `{fix.file_path}:{fix.line_number}`\n"
                description += f"**Issue**: {fix.issue_description}\n"
                description += f"**Solution**: {fix.proposed_solution[:100]}...\n"
                description += f"**Confidence**: {fix.confidence_score:.2f}\n\n"

        # Failed fixes
        if failed_fixes:
            description += "## ❌ Failed Fixes\n\n"
            for fix_data in failed_fixes:
                fix = fix_data["fix_plan"]
                description += f"- **{fix.issue_key}**: {fix_data.get('error', 'Unknown error')}\n"

        # Review notes
        description += "## 🔍 Review Notes\n"
        description += "- All fixes generated by AI analysis\n"
        description += "- Changes follow established coding standards\n"
        description += "- No breaking changes expected\n"
        description += "- Atomic commit with all related fixes\n\n"

        # Impact
        description += "## 🎯 Impact\n"
        description += "- Improved code quality\n"
        description += "- Better maintainability\n"
        description += "- Enhanced security posture\n"
        description += "- Reduced technical debt\n"

        return description

    def run(self, fix_plans: List[FixPlan]) -> Dict[str, Any]:
        """Run the Code Healer workflow with atomic fixes."""
        self.logger.info("🩹 Starting Code Healer LangGraph workflow")

        # Initialize state
        initial_state = CodeHealerWorkflowState(
            project_key=None,
            fix_plans=fix_plans,
            branch_name=None,
            applied_fixes=[],
            failed_fixes=[],
            build_status=None,
            build_output=None,
            build_errors=[],
            workflow_status="initialized",
            error_message=None,
            current_fix_index=0,
            total_fixes=len(fix_plans),
            session_id=None,
            results={}
        )

        try:
            # Run the workflow
            config = {"recursion_limit": 50}
            final_state = self.workflow.invoke(initial_state, config=config)

            self.logger.info("✅ Code Healer workflow completed")
            return final_state["results"]

        except Exception as e:
            self.logger.error(f"❌ Code Healer workflow execution failed: {e}")
            return {
                "status": "error",
                "message": f"Workflow execution failed: {str(e)}",
                "fixes_applied": 0,
                "fixes_failed": len(fix_plans),
                "agent": "CodeHealerAgent",
                "timestamp": datetime.now().isoformat()
            }

    def run_from_storage(self, project_key: str) -> Dict[str, Any]:
        """Load fix plans from storage and run Code Healer workflow."""
        self.logger.info(
            f"📁 Loading fix plans from storage for project: {project_key}")

        try:
            # Load fix plans from storage
            fix_plans = self.fix_plan_storage.get_fix_plans_by_project(
                project_key)

            if not fix_plans:
                return {
                    "status": "warning",
                    "message": f"No fix plans found for project: {project_key}",
                    "fixes_applied": 0,
                    "fixes_failed": 0,
                    "agent": "CodeHealerAgent",
                    "timestamp": datetime.now().isoformat()
                }

            self.logger.info(
                f"📋 Loaded {len(fix_plans)} fix plans from storage")

            # Run workflow with loaded fix plans
            return self.run(fix_plans)

        except Exception as e:
            self.logger.error(f"❌ Failed to load fix plans from storage: {e}")
            return {
                "status": "error",
                "message": f"Failed to load fix plans: {str(e)}",
                "fixes_applied": 0,
                "fixes_failed": 0,
                "agent": "CodeHealerAgent",
                "timestamp": datetime.now().isoformat()
            }

    def visualize_workflow(self) -> str:
        """Get a visual representation of the workflow."""
        return "Code Healer Workflow: Initialize -> Validate Fix Plans -> Create Branch -> Apply Fixes (Atomic) -> Validate Changes -> Maven Clean Build -> Commit & Push -> Create MR -> Finalize"

    def get_mermaid_diagram(self) -> str:
        """Generate Mermaid diagram representation of the workflow."""
        return """
graph TD
    A[Initialize] --> B[Validate Fix Plans]
    B --> C[Create Branch]
    C --> D[Apply Fixes]
    D --> E[Validate Changes]
    E --> F[Maven Clean Build]
    F --> G[Commit & Push]
    G --> H[Create Merge Request]
    H --> I[Finalize]
    
    B --> J[Handle Error]
    C --> J
    D --> J
    E --> J
    G --> J
    
    I --> K[END]
    J --> K
    
    style A fill:#e1f5fe
    style D fill:#fff3e0
    style F fill:#fff9c4
    style G fill:#e8f5e8
    style H fill:#f3e5f5
    style I fill:#c8e6c9
    style J fill:#ffcdd2
    style K fill:#f3e5f5
"""

    def draw_workflow_png(self) -> Optional[bytes]:
        """Generate PNG image of the workflow graph."""
        try:
            return self.workflow.get_graph().draw_mermaid_png()
        except Exception as e:
            self.logger.warning(f"Could not generate PNG: {e}")
            return None
