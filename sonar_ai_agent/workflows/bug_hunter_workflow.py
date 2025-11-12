"""
LangGraph workflow for Bug Hunter Agent.
Implements nodes and edges for SonarQube issue analysis with Langfuse tracking.
"""

from typing import Dict, List, Any, Optional, TypedDict
from datetime import datetime
import json
from langgraph.graph import StateGraph, END
import logging

from ..agents.bug_hunter_agent import BugHunterAgent
from ..models import SonarIssue, FixPlan
from ..config import Config
from ..utils.logger import get_logger


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
    
    # Session tracking
    session_id: Optional[str]
    
    # Results
    results: Dict[str, Any]


class BugHunterWorkflow:
    """LangGraph workflow for Bug Hunter Agent with file-based logging."""
    
    def __init__(self, config: Config):
        """Initialize Bug Hunter workflow."""
        self.config = config
        self.agent = BugHunterAgent(config)
        
        # Initialize file-based logger
        self.logger = get_logger(config, "sonar_ai_agent.workflow")
        
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
        workflow.add_node("process_issues", self._process_issues_node)
        workflow.add_node("finalize", self._finalize_node)
        workflow.add_node("handle_error", self._handle_error_node)
        
        # Set entry point
        workflow.set_entry_point("initialize")
        
        # Add edges
        workflow.add_edge("initialize", "prepare_repository")
        
        # Error handling edges with conditional routing
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
            self._check_issues_available,
            {"process": "process_issues", "finalize": "finalize", "error": "handle_error"}
        )
        
        # Process issues and finalize
        workflow.add_edge("process_issues", "finalize")
        
        # End points
        workflow.add_edge("finalize", END)
        workflow.add_edge("handle_error", END)
        
        # Compile with recursion limit
        return workflow.compile(checkpointer=None, debug=False)
    

    def _initialize_node(self, state: BugHunterWorkflowState) -> BugHunterWorkflowState:
        """Initialize the workflow and start Langfuse tracking."""
        self.logger.info("🚀 Initializing Bug Hunter workflow")
        
        # Start metrics tracking
        self.agent.start_metrics_tracking()
        
        # Initialize session
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
            "session_id": session_id,
            "results": {}
        })
        
        self.logger.info(f"✅ Workflow initialized with session: {session_id}")
        return state
    

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
                
                # Log workflow step
                self.logger.info("Repository preparation completed", 
                               repository_url=self.config.target_repo_url,
                               session_id=state.get("session_id"))
                
        except Exception as e:
            state["error_message"] = f"Repository preparation failed: {str(e)}"
            state["workflow_status"] = "error"
            self.logger.error(f"❌ Repository preparation failed: {e}")
        
        return state
    

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
                
                # Log workflow step
                self.logger.info("SonarQube connection established", 
                               sonar_url=self.config.sonar_url,
                               project_key=self.config.sonar_project_key,
                               session_id=state.get("session_id"))
                
        except Exception as e:
            state["error_message"] = f"SonarQube connection failed: {str(e)}"
            state["workflow_status"] = "error"
            self.logger.error(f"❌ SonarQube connection failed: {e}")
        
        return state
    

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
                
                # Log workflow step
                self.logger.info("Issues fetched and prioritized", 
                               total_issues=len(prioritized_issues),
                               severities=[issue.severity for issue in prioritized_issues[:5]],
                               types=[issue.type for issue in prioritized_issues[:5]],
                               session_id=state.get("session_id"))
                
        except Exception as e:
            state["error_message"] = f"Failed to fetch issues: {str(e)}"
            state["workflow_status"] = "error"
            self.logger.error(f"❌ Failed to fetch issues: {e}")
        
        return state
    

    def _process_issues_node(self, state: BugHunterWorkflowState) -> BugHunterWorkflowState:
        """Process all issues in batch to avoid recursion."""
        issues = state["sonar_issues"]
        max_issues = min(len(issues), self.agent.max_issues_per_run)
        
        self.logger.info(f"🔄 Processing {max_issues} issues in batch")
        
        for i in range(max_issues):
            current_issue = issues[i]
            self.logger.info(f"🔍 Analyzing issue {i + 1}/{max_issues}: {current_issue.key}")
            
            try:
                # Get code context
                code_context = self.agent._get_code_context(current_issue)
                if not code_context:
                    self.logger.warning(f"⚠️ Could not get code context for issue {current_issue.key}")
                    continue
                
                # Analyze with LLM
                analysis = self.agent._analyze_issue_with_llm(current_issue, code_context)
                if not analysis:
                    self.logger.warning(f"⚠️ LLM analysis failed for issue {current_issue.key}")
                    continue
                
                # Create fix plan
                fix_plan = self.agent._create_fix_plan(current_issue, code_context, analysis)
                if fix_plan:
                    state["fix_plans"].append(fix_plan)
                    state["processed_issues"] += 1
                    
                    self.logger.info(f"✅ Fix plan created for {current_issue.key} (confidence: {fix_plan.confidence_score:.2f})")
                    
                    # Log issue analysis
                    self.logger.info("Issue analysis completed", 
                                   issue_key=fix_plan.issue_key,
                                   confidence_score=fix_plan.confidence_score,
                                   estimated_effort=fix_plan.estimated_effort,
                                   file_path=fix_plan.file_path,
                                   session_id=state.get("session_id"))
                else:
                    self.logger.warning(f"⚠️ Failed to create fix plan for {current_issue.key}")
                
            except Exception as e:
                self.logger.error(f"❌ Failed to process issue {current_issue.key}: {e}")
                continue
        
        self.logger.info(f"✅ Batch processing completed: {state['processed_issues']} fix plans created")
        return state
    

    

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
        
        # Final workflow summary
        success_rate = state["processed_issues"] / state["total_issues"] if state["total_issues"] > 0 else 1.0
        
        self.logger.info("Workflow completed successfully", 
                       total_issues=state["total_issues"],
                       processed_issues=state["processed_issues"],
                       fix_plans_created=len(state["fix_plans"]),
                       processing_time_seconds=metrics.processing_time_seconds if metrics else 0,
                       success_rate=success_rate,
                       session_id=state.get("session_id"))
        
        # Log quality metrics
        self.agent.log_quality_score(
            "workflow_success_rate",
            success_rate,
            f"Successfully processed {state['processed_issues']}/{state['total_issues']} issues"
        )
        
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
        
        # Log error details
        self.logger.error("Workflow error occurred", 
                        error_message=error_msg,
                        processed_issues=state.get("processed_issues", 0),
                        total_issues=state.get("total_issues", 0),
                        session_id=state.get("session_id"))
        
        return state
    
    def _check_issues_available(self, state: BugHunterWorkflowState) -> str:
        """Check if there are issues to process."""
        if state["workflow_status"] == "error":
            return "error"
        
        if not state["sonar_issues"] or len(state["sonar_issues"]) == 0:
            self.logger.info("ℹ️ No issues found to process")
            return "finalize"
        
        return "process"
    
    def _check_for_errors(self, state: BugHunterWorkflowState) -> str:
        """Check if there are errors in the current state."""
        if state["workflow_status"] == "error":
            return "error"
        return "continue"
    

    
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
            # Run the workflow with configuration
            config = {"recursion_limit": 50}  # Set reasonable recursion limit
            final_state = self.workflow.invoke(initial_state, config=config)
            
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