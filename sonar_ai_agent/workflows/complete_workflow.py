"""
Complete SonarQube AI Agent Workflow - Integrates Bug Hunter and Code Healer agents.

This workflow orchestrates the complete process:
1. Bug Hunter Agent analyzes SonarQube issues and creates fix plans
2. Code Healer Agent applies the fixes to actual code files
3. Results are consolidated and reported
"""

from typing import Dict, Any, List
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from ..models import WorkflowState, SonarIssue, FixPlan, CodeFix
from ..agents.bug_hunter_agent import BugHunterAgent
from ..agents.code_healer_agent import CodeHealerAgent
from ..integrations.sonarqube_client import SonarQubeClient
from ..config import Config
from ..utils.logger import get_logger


class CompleteSonarWorkflow:
    """Complete workflow that runs both Bug Hunter and Code Healer agents."""
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = get_logger(config, "sonar_ai_agent.CompleteSonarWorkflow")
        
        # Initialize agents
        self.bug_hunter = BugHunterAgent(config)
        self.code_healer = CodeHealerAgent(config)
        self.sonar_client = SonarQubeClient(config)
        
        # Build workflow graph
        self.workflow = self._build_workflow()
    
    def _build_workflow(self) -> StateGraph:
        """Build the LangGraph workflow."""
        workflow = StateGraph(WorkflowState)
        
        # Add nodes
        workflow.add_node("fetch_issues", self._fetch_sonar_issues)
        workflow.add_node("analyze_issues", self._analyze_issues_with_bug_hunter)
        workflow.add_node("apply_fixes", self._apply_fixes_with_code_healer)
        workflow.add_node("consolidate_results", self._consolidate_results)
        workflow.add_node("handle_error", self._handle_error)
        
        # Define edges
        workflow.set_entry_point("fetch_issues")
        
        workflow.add_conditional_edges(
            "fetch_issues",
            self._should_continue_after_fetch,
            {
                "continue": "analyze_issues",
                "error": "handle_error"
            }
        )
        
        workflow.add_conditional_edges(
            "analyze_issues",
            self._should_continue_after_analysis,
            {
                "continue": "apply_fixes",
                "error": "handle_error"
            }
        )
        
        workflow.add_conditional_edges(
            "apply_fixes",
            self._should_continue_after_fixes,
            {
                "continue": "consolidate_results",
                "error": "handle_error"
            }
        )
        
        workflow.add_edge("consolidate_results", END)
        workflow.add_edge("handle_error", END)
        
        return workflow.compile(checkpointer=MemorySaver())
    
    def run(self, project_key: str, severities: List[str] = None) -> Dict[str, Any]:
        """Run the complete workflow."""
        if severities is None:
            severities = ["BLOCKER", "CRITICAL", "MAJOR"]
        
        self.logger.info("Starting complete SonarQube AI workflow", 
                        project_key=project_key,
                        severities=severities)
        
        # Initialize state
        initial_state: WorkflowState = {
            "project_key": project_key,
            "sonar_issues": [],
            "current_issue_index": 0,
            "fix_plans": [],
            "code_fixes": [],
            "merge_requests": [],
            "errors": [],
            "metadata": {
                "severities": severities,
                "start_time": None,
                "end_time": None
            }
        }
        
        try:
            # Run workflow with thread configuration
            config = {"configurable": {"thread_id": f"complete_workflow_{project_key}"}}
            result = self.workflow.invoke(initial_state, config=config)
            
            self.logger.info("Complete workflow finished", 
                           issues_processed=len(result.get("sonar_issues", [])),
                           fix_plans_generated=len(result.get("fix_plans", [])),
                           fixes_applied=len(result.get("code_fixes", [])),
                           merge_requests_created=len(result.get("merge_requests", [])),
                           errors=len(result.get("errors", [])))
            
            return result
            
        except Exception as e:
            self.logger.error(f"Workflow execution failed: {str(e)}")
            raise
    
    def _fetch_sonar_issues(self, state: WorkflowState) -> WorkflowState:
        """Fetch issues from SonarQube."""
        try:
            self.logger.info("Fetching SonarQube issues", 
                           project_key=state["project_key"],
                           severities=state["metadata"]["severities"])
            
            # Fetch issues from SonarQube
            issues = self.sonar_client.fetch_issues(
                project_key=state["project_key"],
                severities=state["metadata"]["severities"]
            )
            
            self.logger.info(f"Fetched {len(issues)} issues from SonarQube")
            
            state["sonar_issues"] = issues
            state["metadata"]["issues_fetched"] = len(issues)
            
            return state
            
        except Exception as e:
            error_msg = f"Failed to fetch SonarQube issues: {str(e)}"
            self.logger.error(error_msg)
            state["errors"].append(error_msg)
            return state
    
    def _analyze_issues_with_bug_hunter(self, state: WorkflowState) -> WorkflowState:
        """Analyze issues using Bug Hunter Agent."""
        try:
            self.logger.info("Starting Bug Hunter analysis", 
                           issues_count=len(state["sonar_issues"]))
            
            # Run Bug Hunter Agent with project key and severities
            bug_hunter_results = self.bug_hunter.process(
                project_key=state["project_key"],
                severities=state["metadata"]["severities"]
            )
            
            # Extract fix plans from results
            fix_plans = bug_hunter_results.get("fix_plans", [])
            
            self.logger.info(f"Bug Hunter generated {len(fix_plans)} fix plans")
            
            state["fix_plans"] = fix_plans
            state["metadata"]["bug_hunter_results"] = bug_hunter_results
            
            return state
            
        except Exception as e:
            error_msg = f"Bug Hunter analysis failed: {str(e)}"
            self.logger.error(error_msg)
            state["errors"].append(error_msg)
            return state
    
    def _apply_fixes_with_code_healer(self, state: WorkflowState) -> WorkflowState:
        """Apply fixes using Code Healer Agent."""
        try:
            self.logger.info("Starting Code Healer fix application", 
                           fix_plans_count=len(state["fix_plans"]))
            
            # Run Code Healer Agent
            code_healer_results = self.code_healer.process(state["fix_plans"])
            
            # Extract applied fixes and merge requests
            applied_fixes = code_healer_results.get("applied_fixes", [])
            merge_requests = code_healer_results.get("merge_requests", [])
            
            self.logger.info(f"Code Healer applied {len(applied_fixes)} fixes and created {len(merge_requests)} merge requests")
            
            state["code_fixes"] = applied_fixes
            state["merge_requests"] = merge_requests
            state["metadata"]["code_healer_results"] = code_healer_results
            
            return state
            
        except Exception as e:
            error_msg = f"Code Healer fix application failed: {str(e)}"
            self.logger.error(error_msg)
            state["errors"].append(error_msg)
            return state
    
    def _consolidate_results(self, state: WorkflowState) -> WorkflowState:
        """Consolidate and finalize results."""
        try:
            self.logger.info("Consolidating workflow results")
            
            # Calculate summary statistics
            total_issues = len(state["sonar_issues"])
            fix_plans_generated = len(state["fix_plans"])
            fixes_applied = len(state["code_fixes"])
            successful_fixes = len([f for f in state["code_fixes"] if f.is_valid])
            merge_requests_created = len(state["merge_requests"])
            
            # Calculate success rates
            analysis_success_rate = fix_plans_generated / total_issues if total_issues > 0 else 0.0
            fix_success_rate = successful_fixes / fix_plans_generated if fix_plans_generated > 0 else 0.0
            overall_success_rate = successful_fixes / total_issues if total_issues > 0 else 0.0
            
            # Update metadata with final results
            state["metadata"].update({
                "total_issues": total_issues,
                "fix_plans_generated": fix_plans_generated,
                "fixes_applied": fixes_applied,
                "successful_fixes": successful_fixes,
                "merge_requests_created": merge_requests_created,
                "analysis_success_rate": analysis_success_rate,
                "fix_success_rate": fix_success_rate,
                "overall_success_rate": overall_success_rate,
                "workflow_status": "completed"
            })
            
            self.logger.info("Workflow results consolidated", 
                           total_issues=total_issues,
                           fix_plans_generated=fix_plans_generated,
                           fixes_applied=fixes_applied,
                           successful_fixes=successful_fixes,
                           merge_requests_created=merge_requests_created,
                           overall_success_rate=overall_success_rate)
            
            return state
            
        except Exception as e:
            error_msg = f"Failed to consolidate results: {str(e)}"
            self.logger.error(error_msg)
            state["errors"].append(error_msg)
            return state
    
    def _handle_error(self, state: WorkflowState) -> WorkflowState:
        """Handle workflow errors."""
        self.logger.error("Workflow encountered errors", 
                         errors=state["errors"],
                         issues_processed=len(state["sonar_issues"]),
                         fix_plans_generated=len(state["fix_plans"]),
                         fixes_applied=len(state["code_fixes"]))
        
        state["metadata"]["workflow_status"] = "failed"
        return state
    
    def _should_continue_after_fetch(self, state: WorkflowState) -> str:
        """Decide whether to continue after fetching issues."""
        if state["errors"]:
            return "error"
        
        if not state["sonar_issues"]:
            self.logger.warning("No issues found to process")
            state["errors"].append("No SonarQube issues found for the specified criteria")
            return "error"
        
        return "continue"
    
    def _should_continue_after_analysis(self, state: WorkflowState) -> str:
        """Decide whether to continue after Bug Hunter analysis."""
        if state["errors"]:
            return "error"
        
        if not state["fix_plans"]:
            self.logger.warning("No fix plans generated by Bug Hunter")
            state["errors"].append("Bug Hunter Agent did not generate any fix plans")
            return "error"
        
        return "continue"
    
    def _should_continue_after_fixes(self, state: WorkflowState) -> str:
        """Decide whether to continue after Code Healer fixes."""
        if state["errors"]:
            return "error"
        
        # Continue even if no fixes were applied (for reporting)
        return "continue"
    
    def health_check(self) -> Dict[str, bool]:
        """Check health of all workflow components."""
        health_status = {
            "sonar_client": False,
            "bug_hunter_agent": False,
            "code_healer_agent": False,
            "overall": False
        }
        
        try:
            # Check SonarQube client
            health_status["sonar_client"] = self.sonar_client.health_check()
            
            # Check Bug Hunter Agent
            health_status["bug_hunter_agent"] = self.bug_hunter.health_check()
            
            # Check Code Healer Agent
            health_status["code_healer_agent"] = self.code_healer.health_check()
            
            # Overall health
            health_status["overall"] = all([
                health_status["sonar_client"],
                health_status["bug_hunter_agent"],
                health_status["code_healer_agent"]
            ])
            
            self.logger.info("Workflow health check completed", **health_status)
            
        except Exception as e:
            self.logger.error(f"Health check failed: {str(e)}")
        
        return health_status


def create_complete_workflow(config: Config) -> CompleteSonarWorkflow:
    """Factory function to create the complete workflow."""
    return CompleteSonarWorkflow(config)