"""
LangGraph workflow for Bug Hunter Agent.
Implements nodes and edges for SonarQube issue analysis and fix plan generation.
"""

from typing import Dict, List, Any, Optional, TypedDict
from datetime import datetime
import json
import time
from langgraph.graph import StateGraph, END
import logging

from ..agents.bug_hunter_agent import BugHunterAgent
from ..models import SonarIssue, FixPlan, AgentMetrics
from ..config import Config
from ..utils.logger import get_logger
from ..utils.fixplan_storage import FixPlanStorage
from ..integrations.sonarqube_client import SonarQubeClient


class BugHunterWorkflowState(TypedDict):
    """State for Bug Hunter workflow."""
    # Input parameters
    project_key: str
    severities: List[str]
    issue_types: List[str]

    # Workflow data
    issues: List[SonarIssue]
    fix_plans: List[FixPlan]

    # Processing state
    current_issue_index: int
    total_issues: int
    processed_issues: List[SonarIssue]
    failed_issues: List[Dict[str, Any]]

    # Status and metadata
    workflow_status: str  # 'running', 'completed', 'error'
    error_message: Optional[str]

    # Session tracking
    session_id: Optional[str]

    # Results
    results: Dict[str, Any]


class BugHunterWorkflow:
    """LangGraph workflow for Bug Hunter Agent."""

    def __init__(self, config: Config):
        """Initialize Bug Hunter workflow."""
        self.config = config
        self.agent = BugHunterAgent(config)

        # Initialize file-based logger
        self.logger = get_logger(config, "sonar_ai_agent.bug_hunter_workflow")

        # Initialize SonarQube client and fix plan storage
        self.sonar_client = SonarQubeClient(config)
        self.fix_plan_storage = FixPlanStorage()

        # Build the workflow graph
        self.workflow = self._build_workflow()

    def _build_workflow(self) -> StateGraph:
        """Build the LangGraph workflow with nodes and edges."""
        workflow = StateGraph(BugHunterWorkflowState)

        # Add nodes
        workflow.add_node("initialize", self._initialize_node)
        workflow.add_node("fetch_issues", self._fetch_issues_node)
        workflow.add_node("analyze_issues", self._analyze_issues_node)
        workflow.add_node("create_fix_plans", self._create_fix_plans_node)
        workflow.add_node("save_fix_plans", self._save_fix_plans_node)
        workflow.add_node("finalize", self._finalize_node)
        workflow.add_node("handle_error", self._handle_error_node)

        # Set entry point
        workflow.set_entry_point("initialize")

        # Add edges
        workflow.add_edge("initialize", "fetch_issues")

        workflow.add_conditional_edges(
            "fetch_issues",
            self._check_for_errors,
            {"continue": "analyze_issues", "error": "handle_error"}
        )

        workflow.add_conditional_edges(
            "analyze_issues",
            self._check_for_errors,
            {"continue": "create_fix_plans", "error": "handle_error"}
        )

        workflow.add_conditional_edges(
            "create_fix_plans",
            self._check_for_errors,
            {"continue": "save_fix_plans", "error": "handle_error"}
        )

        workflow.add_edge("save_fix_plans", "finalize")
        workflow.add_edge("finalize", END)
        workflow.add_edge("handle_error", END)

        return workflow.compile(checkpointer=None, debug=False)

    def _initialize_node(self, state: BugHunterWorkflowState) -> BugHunterWorkflowState:
        """Initialize the Bug Hunter workflow."""
        self.logger.info("🔍 Initializing Bug Hunter workflow")

        # Start metrics tracking
        self.agent.start_metrics_tracking()

        # Initialize session
        session_id = f"bug_hunter_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # Update state
        state.update({
            "issues": [],
            "fix_plans": [],
            "current_issue_index": 0,
            "total_issues": 0,
            "processed_issues": [],
            "failed_issues": [],
            "workflow_status": "running",
            "error_message": None,
            "session_id": session_id,
            "results": {}
        })

        self.logger.info(
            f"✅ Bug Hunter workflow initialized with session: {session_id}")
        return state

    def _fetch_issues_node(self, state: BugHunterWorkflowState) -> BugHunterWorkflowState:
        """Fetch SonarQube issues."""
        self.logger.info("📋 Fetching SonarQube issues")

        try:
            # Fetch issues from SonarQube
            issues = self.sonar_client.get_issues(
                project_key=state["project_key"],
                severities=state["severities"],
                types=state["issue_types"]
            )

            if not issues:
                self.logger.warning("⚠️ No issues found in SonarQube")
                state["issues"] = []
                state["total_issues"] = 0
            else:
                state["issues"] = issues
                state["total_issues"] = len(issues)
                self.logger.info(
                    f"📊 Fetched {len(issues)} issues from SonarQube")

        except Exception as e:
            state["error_message"] = f"Failed to fetch issues: {str(e)}"
            state["workflow_status"] = "error"
            self.logger.error(f"❌ Failed to fetch issues: {e}")

        return state

    def _analyze_issues_node(self, state: BugHunterWorkflowState) -> BugHunterWorkflowState:
        """Analyze SonarQube issues using Bug Hunter agent."""
        issues = state["issues"]
        self.logger.info(f"🔍 Analyzing {len(issues)} issues")

        processed_issues = []
        failed_issues = []

        for i, issue in enumerate(issues):
            try:
                self.logger.info(
                    f"⚡ Analyzing issue {i+1}/{len(issues)}: {issue.key}")

                # Analyze individual issue
                analysis_result = self.agent.analyze_issue(issue)

                if analysis_result["success"]:
                    processed_issues.append(issue)
                    self.logger.info(
                        f"✅ Successfully analyzed issue: {issue.key}")
                else:
                    failed_issues.append({
                        "issue": issue,
                        "error": analysis_result.get("error", "Unknown error")
                    })
                    self.logger.warning(
                        f"⚠️ Failed to analyze issue: {issue.key}")

                # Update current index
                state["current_issue_index"] = i + 1

            except Exception as e:
                failed_issues.append({
                    "issue": issue,
                    "error": str(e)
                })
                self.logger.error(
                    f"❌ Exception analyzing issue {issue.key}: {e}")

        state["processed_issues"] = processed_issues
        state["failed_issues"] = failed_issues

        self.logger.info(
            f"📊 Analysis complete: {len(processed_issues)} successful, {len(failed_issues)} failed")
        return state

    def _create_fix_plans_node(self, state: BugHunterWorkflowState) -> BugHunterWorkflowState:
        """Create fix plans for analyzed issues."""
        processed_issues = state["processed_issues"]
        self.logger.info(
            f"🛠️ Creating fix plans for {len(processed_issues)} issues")

        fix_plans = []

        for issue in processed_issues:
            try:
                self.logger.info(f"📋 Creating fix plan for issue: {issue.key}")

                # Generate fix plan
                fix_plan = self.agent.generate_fix_plan(issue)

                if fix_plan:
                    fix_plans.append(fix_plan)
                    self.logger.info(f"✅ Fix plan created for: {issue.key}")
                else:
                    self.logger.warning(
                        f"⚠️ Could not create fix plan for: {issue.key}")

            except Exception as e:
                self.logger.error(
                    f"❌ Exception creating fix plan for {issue.key}: {e}")

        state["fix_plans"] = fix_plans

        self.logger.info(
            f"📊 Fix plan creation complete: {len(fix_plans)} plans generated")
        return state

    def _save_fix_plans_node(self, state: BugHunterWorkflowState) -> BugHunterWorkflowState:
        """Save fix plans to storage."""
        fix_plans = state["fix_plans"]
        project_key = state["project_key"]

        self.logger.info(f"💾 Saving {len(fix_plans)} fix plans to storage")

        try:
            saved_count = 0
            for fix_plan in fix_plans:
                success = self.fix_plan_storage.save_fix_plan(
                    fix_plan, project_key)
                if success:
                    saved_count += 1

            self.logger.info(
                f"✅ Saved {saved_count}/{len(fix_plans)} fix plans to storage")

            if saved_count != len(fix_plans):
                self.logger.warning(
                    f"⚠️ {len(fix_plans) - saved_count} fix plans failed to save")

        except Exception as e:
            self.logger.error(f"❌ Exception saving fix plans: {e}")
            # Don't fail the workflow for storage issues

        return state

    def _finalize_node(self, state: BugHunterWorkflowState) -> BugHunterWorkflowState:
        """Finalize the Bug Hunter workflow."""
        self.logger.info("🏁 Finalizing Bug Hunter workflow")

        # Stop metrics tracking
        metrics = self.agent.stop_metrics_tracking()

        # Create final results
        processed_count = len(state["processed_issues"])
        failed_count = len(state["failed_issues"])
        fix_plans_count = len(state["fix_plans"])
        total_issues = state["total_issues"]

        results = {
            "status": "success",
            "message": f"Processed {processed_count}/{total_issues} issues and created {fix_plans_count} fix plans",
            "total_issues": total_issues,
            "processed_issues": processed_count,
            "failed_issues": failed_count,
            "total_plans": fix_plans_count,
            "fix_plans": state["fix_plans"],
            "processing_time": metrics.processing_time_seconds if metrics else 0,
            "agent": "BugHunterAgent",
            "timestamp": datetime.now().isoformat()
        }

        state["results"] = results
        state["workflow_status"] = "completed"

        # Final workflow summary
        success_rate = processed_count / total_issues if total_issues > 0 else 1.0

        self.logger.info("Bug Hunter workflow completed",
                         total_issues=total_issues,
                         processed_issues=processed_count,
                         fix_plans_created=fix_plans_count,
                         success_rate=success_rate,
                         processing_time_seconds=metrics.processing_time_seconds if metrics else 0,
                         session_id=state.get("session_id"))

        self.logger.info(
            f"✅ Bug Hunter completed: {fix_plans_count} fix plans created from {processed_count} issues")
        return state

    def _handle_error_node(self, state: BugHunterWorkflowState) -> BugHunterWorkflowState:
        """Handle workflow errors."""
        error_msg = state.get("error_message", "Unknown error")
        self.logger.error(f"❌ Bug Hunter workflow error: {error_msg}")

        # Stop metrics tracking
        self.agent.stop_metrics_tracking()

        # Create error results
        state["results"] = {
            "status": "error",
            "message": error_msg,
            "total_issues": state.get("total_issues", 0),
            "processed_issues": len(state.get("processed_issues", [])),
            "failed_issues": len(state.get("failed_issues", [])),
            "total_plans": len(state.get("fix_plans", [])),
            "agent": "BugHunterAgent",
            "timestamp": datetime.now().isoformat()
        }

        return state

    def _check_for_errors(self, state: BugHunterWorkflowState) -> str:
        """Check if there are errors in the current state."""
        if state["workflow_status"] == "error":
            return "error"
        return "continue"

    def run(self, project_key: str, severities: List[str], issue_types: List[str]) -> Dict[str, Any]:
        """Run the Bug Hunter workflow."""
        self.logger.info("🔍 Starting Bug Hunter LangGraph workflow")

        # Initialize state
        initial_state = BugHunterWorkflowState(
            project_key=project_key,
            severities=severities,
            issue_types=issue_types,
            issues=[],
            fix_plans=[],
            current_issue_index=0,
            total_issues=0,
            processed_issues=[],
            failed_issues=[],
            workflow_status="initialized",
            error_message=None,
            session_id=None,
            results={}
        )

        try:
            # Run the workflow
            config = {"recursion_limit": 50}
            final_state = self.workflow.invoke(initial_state, config=config)

            self.logger.info("✅ Bug Hunter workflow completed")
            return final_state["results"]

        except Exception as e:
            self.logger.error(f"❌ Bug Hunter workflow execution failed: {e}")
            return {
                "status": "error",
                "message": f"Workflow execution failed: {str(e)}",
                "total_issues": 0,
                "processed_issues": 0,
                "failed_issues": 0,
                "total_plans": 0,
                "agent": "BugHunterAgent",
                "timestamp": datetime.now().isoformat()
            }

    def visualize_workflow(self) -> str:
        """Get a visual representation of the workflow."""
        return "Bug Hunter Workflow: Initialize -> Fetch Issues -> Analyze Issues -> Create Fix Plans -> Save Fix Plans -> Finalize"

    def get_mermaid_diagram(self) -> str:
        """Generate Mermaid diagram representation of the workflow."""
        return """
graph TD
    A[Initialize] --> B[Fetch SonarQube Issues]
    B --> C[Analyze Issues]
    C --> D[Create Fix Plans]
    D --> E[Save Fix Plans]
    E --> F[Finalize]
    
    B --> G[Handle Error]
    C --> G
    D --> G
    
    F --> H[END]
    G --> H
    
    style A fill:#e1f5fe
    style B fill:#fff3e0
    style C fill:#e8f5e8
    style D fill:#f3e5f5
    style E fill:#fff9c4
    style F fill:#c8e6c9
    style G fill:#ffcdd2
    style H fill:#f3e5f5
"""

    def draw_workflow_png(self) -> Optional[bytes]:
        """Generate PNG image of the workflow graph."""
        try:
            return self.workflow.get_graph().draw_mermaid_png()
        except Exception as e:
            self.logger.warning(f"Could not generate PNG: {e}")
            return None
