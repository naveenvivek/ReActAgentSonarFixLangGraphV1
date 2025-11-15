"""
Complete LangGraph workflow that combines Bug Hunter and Code Healer.
Implements end-to-end SonarQube issue analysis and fix application.
"""

from typing import Dict, List, Any, Optional, TypedDict
from datetime import datetime
import json
import time
from langgraph.graph import StateGraph, END
import logging

from ..workflows.bug_hunter_workflow import BugHunterWorkflow
from ..workflows.code_healer_workflow import CodeHealerWorkflow
from ..models import SonarIssue, FixPlan, AgentMetrics
from ..config import Config
from ..utils.logger import get_logger


class CompleteWorkflowState(TypedDict):
    """State for Complete workflow (Bug Hunter + Code Healer)."""
    # Input parameters
    project_key: str
    severities: List[str]
    issue_types: List[str]

    # Bug Hunter results
    bug_hunter_results: Dict[str, Any]
    fix_plans: List[FixPlan]

    # Code Healer results
    code_healer_results: Dict[str, Any]

    # Status and metadata
    workflow_status: str  # 'running', 'bug_hunter', 'code_healer', 'completed', 'error'
    error_message: Optional[str]

    # Session tracking
    session_id: Optional[str]

    # Results
    results: Dict[str, Any]


class CompleteSonarWorkflow:
    """Complete LangGraph workflow combining Bug Hunter and Code Healer."""

    def __init__(self, config: Config):
        """Initialize Complete workflow."""
        self.config = config

        # Initialize file-based logger
        self.logger = get_logger(config, "sonar_ai_agent.complete_workflow")

        # Initialize sub-workflows
        self.bug_hunter_workflow = BugHunterWorkflow(config)
        self.code_healer_workflow = CodeHealerWorkflow(config)

        # Build the workflow graph
        self.workflow = self._build_workflow()

    def _build_workflow(self) -> StateGraph:
        """Build the LangGraph workflow with nodes and edges."""
        workflow = StateGraph(CompleteWorkflowState)

        # Add nodes
        workflow.add_node("initialize", self._initialize_node)
        workflow.add_node("run_bug_hunter", self._run_bug_hunter_node)
        workflow.add_node("validate_fix_plans", self._validate_fix_plans_node)
        workflow.add_node("run_code_healer", self._run_code_healer_node)
        workflow.add_node("finalize", self._finalize_node)
        workflow.add_node("handle_error", self._handle_error_node)

        # Set entry point
        workflow.set_entry_point("initialize")

        # Add edges
        workflow.add_edge("initialize", "run_bug_hunter")

        workflow.add_conditional_edges(
            "run_bug_hunter",
            self._check_for_errors,
            {"continue": "validate_fix_plans", "error": "handle_error"}
        )

        workflow.add_conditional_edges(
            "validate_fix_plans",
            self._check_fix_plans_available,
            {"continue": "run_code_healer",
                "skip": "finalize", "error": "handle_error"}
        )

        workflow.add_conditional_edges(
            "run_code_healer",
            self._check_for_errors,
            {"continue": "finalize", "error": "handle_error"}
        )

        workflow.add_edge("finalize", END)
        workflow.add_edge("handle_error", END)

        return workflow.compile(checkpointer=None, debug=False)

    def _initialize_node(self, state: CompleteWorkflowState) -> CompleteWorkflowState:
        """Initialize the Complete workflow."""
        self.logger.info("🚀 Initializing Complete SonarQube workflow")

        # Initialize session
        session_id = f"complete_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # Update state
        state.update({
            "bug_hunter_results": {},
            "fix_plans": [],
            "code_healer_results": {},
            "workflow_status": "running",
            "error_message": None,
            "session_id": session_id,
            "results": {}
        })

        self.logger.info(
            f"✅ Complete workflow initialized with session: {session_id}")
        return state

    def _run_bug_hunter_node(self, state: CompleteWorkflowState) -> CompleteWorkflowState:
        """Run Bug Hunter workflow for issue analysis."""
        self.logger.info("🔍 Running Bug Hunter workflow")

        try:
            state["workflow_status"] = "bug_hunter"

            # Run Bug Hunter workflow
            bug_hunter_results = self.bug_hunter_workflow.run(
                project_key=state["project_key"],
                severities=state["severities"],
                issue_types=state["issue_types"]
            )

            state["bug_hunter_results"] = bug_hunter_results

            # Extract fix plans
            if bug_hunter_results.get("status") == "success":
                fix_plans = bug_hunter_results.get("fix_plans", [])
                state["fix_plans"] = fix_plans
                self.logger.info(
                    f"✅ Bug Hunter completed: {len(fix_plans)} fix plans created")
            else:
                state["error_message"] = f"Bug Hunter failed: {bug_hunter_results.get('message', 'Unknown error')}"
                state["workflow_status"] = "error"
                self.logger.error(
                    f"❌ Bug Hunter failed: {state['error_message']}")

        except Exception as e:
            state["error_message"] = f"Bug Hunter workflow failed: {str(e)}"
            state["workflow_status"] = "error"
            self.logger.error(f"❌ Bug Hunter workflow exception: {e}")

        return state

    def _validate_fix_plans_node(self, state: CompleteWorkflowState) -> CompleteWorkflowState:
        """Validate fix plans before running Code Healer."""
        fix_plans = state.get("fix_plans", [])
        self.logger.info(f"📋 Validating {len(fix_plans)} fix plans")

        if not fix_plans:
            self.logger.warning("⚠️ No fix plans available for Code Healer")
            state["workflow_status"] = "no_fix_plans"
            return state

        # Validate fix plans quality
        valid_plans = []
        for plan in fix_plans:
            if self._is_valid_fix_plan(plan):
                valid_plans.append(plan)

        if not valid_plans:
            self.logger.warning("⚠️ No valid fix plans found")
            state["workflow_status"] = "no_valid_fix_plans"
            return state

        state["fix_plans"] = valid_plans
        self.logger.info(
            f"✅ Validated {len(valid_plans)} fix plans for Code Healer")
        return state

    def _run_code_healer_node(self, state: CompleteWorkflowState) -> CompleteWorkflowState:
        """Run Code Healer workflow for fix application."""
        self.logger.info("🩹 Running Code Healer workflow")

        try:
            state["workflow_status"] = "code_healer"

            # Run Code Healer workflow with fix plans
            code_healer_results = self.code_healer_workflow.run(
                state["fix_plans"])

            state["code_healer_results"] = code_healer_results

            if code_healer_results.get("status") == "success":
                fixes_applied = code_healer_results.get("fixes_applied", 0)
                self.logger.info(
                    f"✅ Code Healer completed: {fixes_applied} fixes applied")
            else:
                self.logger.warning(
                    f"⚠️ Code Healer issues: {code_healer_results.get('message', 'Unknown issue')}")

        except Exception as e:
            state["error_message"] = f"Code Healer workflow failed: {str(e)}"
            state["workflow_status"] = "error"
            self.logger.error(f"❌ Code Healer workflow exception: {e}")

        return state

    def _finalize_node(self, state: CompleteWorkflowState) -> CompleteWorkflowState:
        """Finalize the Complete workflow."""
        self.logger.info("🏁 Finalizing Complete workflow")

        # Collect results from both workflows
        bug_hunter_results = state.get("bug_hunter_results", {})
        code_healer_results = state.get("code_healer_results", {})

        # Calculate overall metrics
        total_issues = bug_hunter_results.get("total_issues", 0)
        processed_issues = bug_hunter_results.get("processed_issues", 0)
        fix_plans_generated = bug_hunter_results.get("total_plans", 0)
        fixes_applied = code_healer_results.get("fixes_applied", 0)
        successful_fixes = fixes_applied  # Assuming applied fixes are successful

        # Create comprehensive results
        results = {
            "status": "success",
            "message": f"Complete workflow finished: {fixes_applied} fixes applied from {fix_plans_generated} plans",
            "metadata": {
                "workflow_status": "completed",
                "total_issues": total_issues,
                "processed_issues": processed_issues,
                "fix_plans_generated": fix_plans_generated,
                "fixes_applied": fixes_applied,
                "successful_fixes": successful_fixes,
                "failed_fixes": code_healer_results.get("fixes_failed", 0),
                "merge_requests_created": 1 if code_healer_results.get("merge_request_url") else 0,
                "overall_success_rate": (successful_fixes / fix_plans_generated) if fix_plans_generated > 0 else 0.0,
                "bug_hunter_processing_time": bug_hunter_results.get("processing_time", 0),
                "code_healer_processing_time": code_healer_results.get("processing_time", 0),
                "session_id": state.get("session_id")
            },
            "bug_hunter_results": bug_hunter_results,
            "code_healer_results": code_healer_results,
            "timestamp": datetime.now().isoformat()
        }

        # Add merge requests info
        merge_requests = []
        mr_url = code_healer_results.get("merge_request_url")
        if mr_url:
            merge_requests.append(mr_url)
        results["merge_requests"] = merge_requests

        # Add errors if any
        errors = []
        if state.get("error_message"):
            errors.append(state["error_message"])
        if bug_hunter_results.get("status") == "error":
            errors.append(f"Bug Hunter: {bug_hunter_results.get('message')}")
        if code_healer_results.get("status") == "error":
            errors.append(f"Code Healer: {code_healer_results.get('message')}")
        results["errors"] = errors

        state["results"] = results
        state["workflow_status"] = "completed"

        # Final workflow summary
        self.logger.info("Complete workflow finished",
                         total_issues=total_issues,
                         fix_plans_generated=fix_plans_generated,
                         fixes_applied=fixes_applied,
                         merge_requests_created=len(merge_requests),
                         session_id=state.get("session_id"))

        self.logger.info(
            f"✅ Complete workflow finished: {fixes_applied} fixes applied")
        return state

    def _handle_error_node(self, state: CompleteWorkflowState) -> CompleteWorkflowState:
        """Handle workflow errors."""
        error_msg = state.get("error_message", "Unknown error")
        self.logger.error(f"❌ Complete workflow error: {error_msg}")

        # Create error results
        state["results"] = {
            "status": "error",
            "message": error_msg,
            "metadata": {
                "workflow_status": "error",
                "total_issues": 0,
                "fix_plans_generated": 0,
                "fixes_applied": 0,
                "session_id": state.get("session_id")
            },
            "bug_hunter_results": state.get("bug_hunter_results", {}),
            "code_healer_results": state.get("code_healer_results", {}),
            "timestamp": datetime.now().isoformat()
        }

        return state

    def _check_for_errors(self, state: CompleteWorkflowState) -> str:
        """Check if there are errors in the current state."""
        if state["workflow_status"] == "error":
            return "error"
        return "continue"

    def _check_fix_plans_available(self, state: CompleteWorkflowState) -> str:
        """Check if fix plans are available for Code Healer."""
        if state["workflow_status"] == "error":
            return "error"

        workflow_status = state.get("workflow_status")
        if workflow_status in ["no_fix_plans", "no_valid_fix_plans"]:
            return "skip"

        return "continue"

    def _is_valid_fix_plan(self, fix_plan: FixPlan) -> bool:
        """Validate individual fix plan."""
        return (
            fix_plan.issue_key and
            fix_plan.file_path and
            fix_plan.proposed_solution and
            fix_plan.confidence_score > 0.5
        )

    def run(self, project_key: str, severities: List[str], issue_types: List[str] = None) -> Dict[str, Any]:
        """Run the Complete workflow."""
        self.logger.info("🚀 Starting Complete SonarQube LangGraph workflow")

        # Use default issue types if not provided
        if issue_types is None:
            issue_types = ["BUG", "VULNERABILITY", "CODE_SMELL"]

        # Initialize state
        initial_state = CompleteWorkflowState(
            project_key=project_key,
            severities=severities,
            issue_types=issue_types,
            bug_hunter_results={},
            fix_plans=[],
            code_healer_results={},
            workflow_status="initialized",
            error_message=None,
            session_id=None,
            results={}
        )

        try:
            # Run the workflow
            config = {"recursion_limit": 50}
            final_state = self.workflow.invoke(initial_state, config=config)

            self.logger.info("✅ Complete workflow finished")
            return final_state["results"]

        except Exception as e:
            self.logger.error(f"❌ Complete workflow execution failed: {e}")
            return {
                "status": "error",
                "message": f"Complete workflow execution failed: {str(e)}",
                "metadata": {
                    "workflow_status": "error",
                    "total_issues": 0,
                    "fix_plans_generated": 0,
                    "fixes_applied": 0
                },
                "timestamp": datetime.now().isoformat()
            }

    def visualize_workflow(self) -> str:
        """Get a visual representation of the workflow."""
        return "Complete Workflow: Initialize -> Bug Hunter (Analysis) -> Validate Fix Plans -> Code Healer (Apply Fixes) -> Finalize"

    def get_mermaid_diagram(self) -> str:
        """Generate Mermaid diagram representation of the workflow."""
        return """
graph TD
    A[Initialize] --> B[Run Bug Hunter]
    B --> C[Validate Fix Plans]
    C --> D[Run Code Healer]
    D --> E[Finalize]
    
    B --> F[Handle Error]
    C --> F
    D --> F
    C --> E
    
    E --> G[END]
    F --> G
    
    style A fill:#e1f5fe
    style B fill:#fff3e0
    style C fill:#e8f5e8
    style D fill:#f3e5f5
    style E fill:#c8e6c9
    style F fill:#ffcdd2
    style G fill:#f3e5f5
"""

    def draw_workflow_png(self) -> Optional[bytes]:
        """Generate PNG image of the workflow graph."""
        try:
            return self.workflow.get_graph().draw_mermaid_png()
        except Exception as e:
            self.logger.warning(f"Could not generate PNG: {e}")
            return None
