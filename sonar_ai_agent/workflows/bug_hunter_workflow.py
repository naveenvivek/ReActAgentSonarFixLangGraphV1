"""
LangGraph workflow for Bug Hunter Agent.
Implements nodes and edges for SonarQube issue analysis with Langfuse tracking.
"""

from typing import Dict, List, Any, Optional, TypedDict
from datetime import datetime
import json
from langgraph.graph import StateGraph, END
from langfuse import observe
import logging

from ..agents.bug_hunter_agent import BugHunterAgent
from ..models import SonarIssue, FixPlan
from ..config import Config


class BugHunterWorkflowState(TypedDict):
    """State for Bug Hunter workflow."""
    # Input parameters
    project_key: Optional[str]
    severities: Optional[List[str]]
    issue_types: Optional[List[str]]
    
    # Workflow data
    sonar_issues: List[SonarIssue]
    fix_plans: List[FixPlan]
    current_issue_index: int
    
    # Status and metadata
    workflow_status: str  # 'running', 'completed', 'error'
    error_message: Optional[str]
    processed_issues: int
    total_issues: int
    
    # Langfuse tracking
    langfuse_trace_id: Optional[str]
    langfuse_session_id: Optional[str]
    
    # Results
    results: Dict[str, Any]


class BugHunterWorkflow:
    """LangGraph workflow for Bug Hunter Agent with Langfuse integration."""
    
    def __init__(self, config: Config):
        """Initialize Bug Hunter workflow."""
        self.config = config
        self.agent = BugHunterAgent(config)
        
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        
        # Add console handler if not exists
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setLevel(logging.INFO)
            formatter = logging.Formatter('%(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
        
        # Build the workflow graph
        self.workflow = self._build_workflow()
    
    def _build_workflow(self) -> StateGraph:
        """Build the LangGraph workflow with nodes and edges."""
        workflow = StateGraph(BugHunterWorkflowState)
        
        # Add nodes
        workflow.add_node("initialize", self._initialize_node)
        workflow.add_node("prepare_repository", self._prepare_repository_node)
        workflow.add_node("connect_sonarqube", self._connect_sonarqube_node)
        workflow.add_node("fetch_issues", self._fetch_issues_node)
        workflow.add_node("analyze_issue", self._analyze_issue_node)
        workflow.add_node("create_fix_plan", self._create_fix_plan_node)
        workflow.add_node("update_langfuse", self._update_langfuse_node)
        workflow.add_node("finalize", self._finalize_node)
        workflow.add_node("handle_error", self._handle_error_node)
        
        # Set entry point
        workflow.set_entry_point("initialize")
        
        # Add edges
        workflow.add_edge("initialize", "prepare_repository")
        workflow.add_edge("prepare_repository", "connect_sonarqube")
        workflow.add_edge("connect_sonarqube", "fetch_issues")
        workflow.add_edge("fetch_issues", "analyze_issue")
        workflow.add_edge("analyze_issue", "create_fix_plan")
        workflow.add_edge("create_fix_plan", "update_langfuse")
        
        # Conditional edges
        workflow.add_conditional_edges(
            "update_langfuse",
            self._should_continue_processing,
            {
                "continue": "analyze_issue",
                "finalize": "finalize",
                "error": "handle_error"
            }
        )
        
        # Error handling edges
        workflow.add_conditional_edges(
            "prepare_repository",
            self._check_for_errors,
            {"continue": "connect_sonarqube", "error": "handle_error"}
        )
        
        workflow.add_conditional_edges(
            "connect_sonarqube", 
            self._check_for_errors,
            {"continue": "fetch_issues", "error": "handle_error"}
        )
        
        workflow.add_conditional_edges(
            "fetch_issues",
            self._check_for_errors,
            {"continue": "analyze_issue", "error": "handle_error"}
        )
        
        # End points
        workflow.add_edge("finalize", END)
        workflow.add_edge("handle_error", END)
        
        return workflow.compile()
    
    @observe(name="bug_hunter_initialize")
    def _initialize_node(self, state: BugHunterWorkflowState) -> BugHunterWorkflowState:
        """Initialize the workflow and start Langfuse tracking."""
        self.logger.info("🚀 Initializing Bug Hunter workflow")
        
        # Start metrics tracking
        self.agent.start_metrics_tracking()
        
        # Initialize Langfuse session
        session_id = f"bug_hunter_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Update state
        state.update({
            "workflow_status": "running",
            "error_message": None,
            "processed_issues": 0,
            "total_issues": 0,
            "current_issue_index": 0,
            "sonar_issues": [],
            "fix_plans": [],
            "langfuse_session_id": session_id,
            "results": {}
        })
        
        # Initialize Langfuse tracking
        try:
            trace_id = f"trace_{session_id}"
            state["langfuse_trace_id"] = trace_id
            self.logger.info(f"Langfuse tracking initialized: {trace_id}")
        except Exception as e:
            self.logger.warning(f"Failed to initialize Langfuse tracking: {e}")
        
        self.logger.info(f"✅ Workflow initialized with session: {session_id}")
        return state
    
    @observe(name="bug_hunter_prepare_repository")
    def _prepare_repository_node(self, state: BugHunterWorkflowState) -> BugHunterWorkflowState:
        """Prepare the target repository."""
        self.logger.info("📁 Preparing target repository")
        
        try:
            success = self.agent._prepare_repository()
            if not success:
                state["error_message"] = "Failed to prepare repository"
                state["workflow_status"] = "error"
            else:
                self.logger.info("✅ Repository prepared successfully")
                
                # Log to Langfuse
                self._log_to_langfuse("repository_prepared", state, {
                    "repository_url": self.config.target_repo_url
                })
                
        except Exception as e:
            state["error_message"] = f"Repository preparation failed: {str(e)}"
            state["workflow_status"] = "error"
            self.logger.error(f"❌ Repository preparation failed: {e}")
        
        return state
    
    @observe(name="bug_hunter_connect_sonarqube")
    def _connect_sonarqube_node(self, state: BugHunterWorkflowState) -> BugHunterWorkflowState:
        """Connect to SonarQube and validate project."""
        self.logger.info("🔗 Connecting to SonarQube")
        
        try:
            success = self.agent._validate_sonar_connection()
            if not success:
                state["error_message"] = "Failed to connect to SonarQube"
                state["workflow_status"] = "error"
            else:
                self.logger.info("✅ SonarQube connection validated")
                
                # Log to Langfuse
                self._log_to_langfuse("sonarqube_connected", state, {
                    "sonar_url": self.config.sonar_url,
                    "project_key": self.config.sonar_project_key
                })
                
        except Exception as e:
            state["error_message"] = f"SonarQube connection failed: {str(e)}"
            state["workflow_status"] = "error"
            self.logger.error(f"❌ SonarQube connection failed: {e}")
        
        return state
    
    @observe(name="bug_hunter_fetch_issues")
    def _fetch_issues_node(self, state: BugHunterWorkflowState) -> BugHunterWorkflowState:
        """Fetch issues from SonarQube."""
        self.logger.info("📊 Fetching issues from SonarQube")
        
        try:
            issues = self.agent._fetch_sonar_issues(
                project_key=state.get("project_key"),
                severities=state.get("severities"),
                issue_types=state.get("issue_types")
            )
            
            if not issues:
                self.logger.info("ℹ️ No issues found to process")
                state["workflow_status"] = "completed"
                state["results"] = {"message": "No issues found", "fix_plans": []}
            else:
                # Prioritize issues
                prioritized_issues = self.agent._prioritize_issues(issues)
                
                state["sonar_issues"] = prioritized_issues
                state["total_issues"] = len(prioritized_issues)
                state["current_issue_index"] = 0
                
                self.logger.info(f"✅ Fetched and prioritized {len(prioritized_issues)} issues")
                
                # Log to Langfuse
                self._log_to_langfuse("issues_fetched", state, {
                    "total_issues": len(prioritized_issues),
                    "severities": [issue.severity for issue in prioritized_issues[:5]],  # First 5
                    "types": [issue.type for issue in prioritized_issues[:5]]
                })
                
        except Exception as e:
            state["error_message"] = f"Failed to fetch issues: {str(e)}"
            state["workflow_status"] = "error"
            self.logger.error(f"❌ Failed to fetch issues: {e}")
        
        return state
    
    @observe(name="bug_hunter_analyze_issue")
    def _analyze_issue_node(self, state: BugHunterWorkflowState) -> BugHunterWorkflowState:
        """Analyze current issue with LLM."""
        current_index = state["current_issue_index"]
        issues = state["sonar_issues"]
        
        if current_index >= len(issues):
            state["workflow_status"] = "completed"
            return state
        
        current_issue = issues[current_index]
        self.logger.info(f"🔍 Analyzing issue {current_index + 1}/{len(issues)}: {current_issue.key}")
        
        try:
            # Get code context
            code_context = self.agent._get_code_context(current_issue)
            if not code_context:
                self.logger.warning(f"⚠️ Could not get code context for issue {current_issue.key}")
                state["current_issue_index"] += 1
                return state
            
            # Analyze with LLM
            analysis = self.agent._analyze_issue_with_llm(current_issue, code_context)
            if not analysis:
                self.logger.warning(f"⚠️ LLM analysis failed for issue {current_issue.key}")
                state["current_issue_index"] += 1
                return state
            
            # Store analysis in state for next node
            state["current_analysis"] = {
                "issue": current_issue,
                "code_context": code_context,
                "analysis": analysis
            }
            
            self.logger.info(f"✅ Issue analysis completed for {current_issue.key}")
            
        except Exception as e:
            self.logger.error(f"❌ Failed to analyze issue {current_issue.key}: {e}")
            state["current_issue_index"] += 1
        
        return state
    
    @observe(name="bug_hunter_create_fix_plan")
    def _create_fix_plan_node(self, state: BugHunterWorkflowState) -> BugHunterWorkflowState:
        """Create fix plan from analysis."""
        if "current_analysis" not in state:
            state["current_issue_index"] += 1
            return state
        
        analysis_data = state["current_analysis"]
        issue = analysis_data["issue"]
        code_context = analysis_data["code_context"]
        analysis = analysis_data["analysis"]
        
        self.logger.info(f"📋 Creating fix plan for issue {issue.key}")
        
        try:
            fix_plan = self.agent._create_fix_plan(issue, code_context, analysis)
            if fix_plan:
                state["fix_plans"].append(fix_plan)
                state["processed_issues"] += 1
                
                self.logger.info(f"✅ Fix plan created for {issue.key} (confidence: {fix_plan.confidence_score:.2f})")
            else:
                self.logger.warning(f"⚠️ Failed to create fix plan for {issue.key}")
            
            # Clean up current analysis
            del state["current_analysis"]
            
        except Exception as e:
            self.logger.error(f"❌ Failed to create fix plan for {issue.key}: {e}")
        
        return state
    
    @observe(name="bug_hunter_update_langfuse")
    def _update_langfuse_node(self, state: BugHunterWorkflowState) -> BugHunterWorkflowState:
        """Update Langfuse with issue analysis and fix plan."""
        if not state["fix_plans"]:
            state["current_issue_index"] += 1
            return state
        
        latest_fix_plan = state["fix_plans"][-1]
        self.logger.info(f"📊 Updating Langfuse with fix plan for {latest_fix_plan.issue_key}")
        
        try:
            # Create detailed Langfuse event for this issue
            self._log_to_langfuse("issue_analyzed", state, {
                "issue_key": latest_fix_plan.issue_key,
                "file_path": latest_fix_plan.file_path,
                "line_number": latest_fix_plan.line_number,
                "issue_description": latest_fix_plan.issue_description,
                "confidence_score": latest_fix_plan.confidence_score,
                "estimated_effort": latest_fix_plan.estimated_effort,
                "problem_analysis": latest_fix_plan.problem_analysis[:200] + "..." if len(latest_fix_plan.problem_analysis) > 200 else latest_fix_plan.problem_analysis,
                "proposed_solution": latest_fix_plan.proposed_solution[:200] + "..." if len(latest_fix_plan.proposed_solution) > 200 else latest_fix_plan.proposed_solution
            })
            
            # Create quality scores
            try:
                self.agent.create_langfuse_score(
                    name="fix_plan_confidence",
                    value=latest_fix_plan.confidence_score,
                    comment=f"Confidence score for issue {latest_fix_plan.issue_key}"
                )
                
                # Create effort score (convert to numeric)
                effort_scores = {"LOW": 0.3, "MEDIUM": 0.6, "HIGH": 0.9}
                effort_score = effort_scores.get(latest_fix_plan.estimated_effort, 0.5)
                
                self.agent.create_langfuse_score(
                    name="fix_effort_estimate",
                    value=effort_score,
                    comment=f"Effort estimate for issue {latest_fix_plan.issue_key}: {latest_fix_plan.estimated_effort}"
                )
            except Exception as score_error:
                self.logger.warning(f"Failed to create Langfuse scores: {score_error}")
            
            self.logger.info(f"✅ Langfuse updated for issue {latest_fix_plan.issue_key}")
            
        except Exception as e:
            self.logger.error(f"❌ Failed to update Langfuse: {e}")
        
        # Move to next issue
        state["current_issue_index"] += 1
        return state
    
    @observe(name="bug_hunter_finalize")
    def _finalize_node(self, state: BugHunterWorkflowState) -> BugHunterWorkflowState:
        """Finalize the workflow and create summary."""
        self.logger.info("🏁 Finalizing Bug Hunter workflow")
        
        # Stop metrics tracking
        metrics = self.agent.stop_metrics_tracking()
        
        # Create final results
        results = {
            "status": "success",
            "message": f"Processed {state['processed_issues']} out of {state['total_issues']} issues",
            "fix_plans": state["fix_plans"],
            "total_plans": len(state["fix_plans"]),
            "processing_time": metrics.processing_time_seconds if metrics else 0,
            "agent": "BugHunterAgent",
            "timestamp": datetime.now().isoformat()
        }
        
        state["results"] = results
        state["workflow_status"] = "completed"
        
        # Final Langfuse summary
        self._log_to_langfuse("workflow_completed", state, {
            "total_issues": state["total_issues"],
            "processed_issues": state["processed_issues"],
            "fix_plans_created": len(state["fix_plans"]),
            "processing_time_seconds": metrics.processing_time_seconds if metrics else 0,
            "success_rate": state["processed_issues"] / state["total_issues"] if state["total_issues"] > 0 else 0
        })
        
        # Overall workflow score
        try:
            success_rate = state["processed_issues"] / state["total_issues"] if state["total_issues"] > 0 else 1.0
            self.agent.create_langfuse_score(
                name="workflow_success_rate",
                value=success_rate,
                comment=f"Successfully processed {state['processed_issues']}/{state['total_issues']} issues"
            )
        except Exception as e:
            self.logger.warning(f"Failed to create workflow success score: {e}")
        
        self.logger.info(f"✅ Workflow completed: {len(state['fix_plans'])} fix plans created")
        return state
    
    def _handle_error_node(self, state: BugHunterWorkflowState) -> BugHunterWorkflowState:
        """Handle workflow errors."""
        error_msg = state.get("error_message", "Unknown error")
        self.logger.error(f"❌ Workflow error: {error_msg}")
        
        # Stop metrics tracking
        self.agent.stop_metrics_tracking()
        
        # Create error results
        state["results"] = {
            "status": "error",
            "message": error_msg,
            "fix_plans": state.get("fix_plans", []),
            "total_plans": len(state.get("fix_plans", [])),
            "agent": "BugHunterAgent",
            "timestamp": datetime.now().isoformat()
        }
        
        # Log error to Langfuse
        self._log_to_langfuse("workflow_error", state, {
            "error_message": error_msg,
            "processed_issues": state.get("processed_issues", 0),
            "total_issues": state.get("total_issues", 0)
        })
        
        return state
    
    def _should_continue_processing(self, state: BugHunterWorkflowState) -> str:
        """Determine if we should continue processing more issues."""
        if state["workflow_status"] == "error":
            return "error"
        
        if state["current_issue_index"] >= len(state["sonar_issues"]):
            return "finalize"
        
        # Limit processing to avoid long runs
        if state["processed_issues"] >= self.agent.max_issues_per_run:
            return "finalize"
        
        return "continue"
    
    def _check_for_errors(self, state: BugHunterWorkflowState) -> str:
        """Check if there are errors in the current state."""
        if state["workflow_status"] == "error":
            return "error"
        return "continue"
    
    def _log_to_langfuse(self, event_name: str, state: BugHunterWorkflowState, metadata: Dict[str, Any]):
        """Helper method to safely log events to Langfuse."""
        try:
            self.agent.langfuse.create_event(
                name=event_name,
                session_id=state.get("langfuse_session_id"),
                metadata=metadata
            )
            self.logger.debug(f"Logged to Langfuse: {event_name}")
        except Exception as e:
            self.logger.warning(f"Failed to log {event_name} to Langfuse: {e}")
    
    def run(self, project_key: Optional[str] = None,
            severities: Optional[List[str]] = None,
            issue_types: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Run the Bug Hunter workflow.
        
        Args:
            project_key: SonarQube project key
            severities: List of severities to process
            issue_types: List of issue types to process
            
        Returns:
            Workflow results
        """
        self.logger.info("🚀 Starting Bug Hunter LangGraph workflow")
        
        # Initialize state
        initial_state = BugHunterWorkflowState(
            project_key=project_key,
            severities=severities or ['BLOCKER', 'CRITICAL', 'MAJOR'],
            issue_types=issue_types or ['BUG', 'VULNERABILITY', 'CODE_SMELL'],
            sonar_issues=[],
            fix_plans=[],
            current_issue_index=0,
            workflow_status="initialized",
            error_message=None,
            processed_issues=0,
            total_issues=0,
            langfuse_trace_id=None,
            langfuse_session_id=None,
            results={}
        )
        
        try:
            # Run the workflow
            final_state = self.workflow.invoke(initial_state)
            
            self.logger.info("✅ Bug Hunter workflow completed")
            return final_state["results"]
            
        except Exception as e:
            self.logger.error(f"❌ Workflow execution failed: {e}")
            return {
                "status": "error",
                "message": f"Workflow execution failed: {str(e)}",
                "fix_plans": [],
                "total_plans": 0,
                "agent": "BugHunterAgent",
                "timestamp": datetime.now().isoformat()
            }
    
    def visualize_workflow(self) -> str:
        """Get a visual representation of the workflow."""
        try:
            # This would generate a visual graph of the workflow
            return "Workflow visualization: Initialize -> Prepare Repository -> Connect SonarQube -> Fetch Issues -> Analyze Issue -> Create Fix Plan -> Update Langfuse -> (Continue/Finalize)"
        except Exception as e:
            return f"Could not generate visualization: {e}"
    
    def get_mermaid_diagram(self) -> str:
        """Generate Mermaid diagram representation of the workflow."""
        return """
graph TD
    A[Initialize] --> B[Prepare Repository]
    B --> C[Connect SonarQube]
    C --> D[Fetch Issues]
    D --> E[Analyze Issue]
    E --> F[Create Fix Plan]
    F --> G[Update Langfuse]
    G --> H{More Issues?}
    H -->|Yes| E
    H -->|No| I[Finalize]
    
    B --> J[Handle Error]
    C --> J
    D --> J
    E --> J
    F --> J
    G --> J
    
    I --> K[END]
    J --> K
    
    style A fill:#e1f5fe
    style I fill:#c8e6c9
    style J fill:#ffcdd2
    style K fill:#f3e5f5
"""
    
    def draw_workflow_png(self) -> bytes:
        """Generate PNG image of the workflow graph."""
        try:
            # Try to use the LangGraph built-in visualization
            return self.workflow.get_graph().draw_mermaid_png()
        except Exception as e:
            self.logger.warning(f"Could not generate PNG: {e}")
            return None
    
    def save_workflow_diagram(self, filename: str = "workflow_diagram.png") -> bool:
        """Save workflow diagram as PNG file."""
        try:
            png_data = self.draw_workflow_png()
            if png_data:
                with open(filename, 'wb') as f:
                    f.write(png_data)
                self.logger.info(f"Workflow diagram saved as {filename}")
                return True
            else:
                # Fallback: save Mermaid text
                mermaid_text = self.get_mermaid_diagram()
                with open(filename.replace('.png', '.mmd'), 'w') as f:
                    f.write(mermaid_text)
                self.logger.info(f"Mermaid diagram saved as {filename.replace('.png', '.mmd')}")
                return True
        except Exception as e:
            self.logger.error(f"Failed to save workflow diagram: {e}")
            return False