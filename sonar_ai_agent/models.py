"""
Data models for SonarQube AI Agent system.
Defines the core data structures used throughout the workflow.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import List, Dict, Any, Optional, TypedDict


@dataclass
class SonarIssue:
    """Model for SonarQube code quality issues."""
    
    key: str
    rule: str
    severity: str  # BLOCKER, CRITICAL, MAJOR, MINOR, INFO
    component: str  # File path
    line: int
    message: str
    type: str  # BUG, VULNERABILITY, CODE_SMELL
    status: str
    creation_date: datetime
    tags: List[str]
    
    def __post_init__(self):
        """Validate severity and type values."""
        valid_severities = {"BLOCKER", "CRITICAL", "MAJOR", "MINOR", "INFO"}
        valid_types = {"BUG", "VULNERABILITY", "CODE_SMELL"}
        
        if self.severity not in valid_severities:
            raise ValueError(f"Invalid severity: {self.severity}. Must be one of {valid_severities}")
        
        if self.type not in valid_types:
            raise ValueError(f"Invalid type: {self.type}. Must be one of {valid_types}")


@dataclass
class FixPlan:
    """Model for AI-generated fix plans from Bug Hunter Agent."""
    
    issue_key: str
    issue_description: str
    file_path: str
    line_number: int
    problem_analysis: str
    proposed_solution: str
    code_context: str
    potential_side_effects: List[str]
    confidence_score: float  # 0.0 to 1.0
    estimated_effort: str  # LOW, MEDIUM, HIGH
    
    def __post_init__(self):
        """Validate confidence score and effort values."""
        if not 0.0 <= self.confidence_score <= 1.0:
            raise ValueError(f"Confidence score must be between 0.0 and 1.0, got {self.confidence_score}")
        
        valid_efforts = {"LOW", "MEDIUM", "HIGH"}
        if self.estimated_effort not in valid_efforts:
            raise ValueError(f"Invalid effort: {self.estimated_effort}. Must be one of {valid_efforts}")


@dataclass
class CodeFix:
    """Model for generated code fixes from Code Healer Agent."""
    
    fix_plan: FixPlan
    original_code: str
    fixed_code: str
    diff: str
    validation_status: bool
    validation_errors: List[str]
    branch_name: str
    commit_message: str
    
    @property
    def is_valid(self) -> bool:
        """Check if the fix passed validation."""
        return self.validation_status and len(self.validation_errors) == 0


class WorkflowState(TypedDict):
    """State model for LangGraph workflow execution."""
    
    # Configuration
    project_key: str
    
    # Issue Processing
    sonar_issues: List[SonarIssue]
    current_issue_index: int
    
    # Fix Generation
    fix_plans: List[FixPlan]
    code_fixes: List[CodeFix]
    
    # Results
    merge_requests: List[str]  # List of created MR URLs
    
    # Error Handling
    errors: List[str]
    
    # Metadata
    metadata: Dict[str, Any]


@dataclass
class AgentMetrics:
    """Metrics for tracking agent performance."""
    
    agent_name: str
    start_time: datetime
    end_time: Optional[datetime] = None
    issues_processed: int = 0
    fixes_generated: int = 0
    fixes_validated: int = 0
    merge_requests_created: int = 0
    errors_encountered: int = 0
    
    @property
    def processing_time_seconds(self) -> Optional[float]:
        """Calculate processing time in seconds."""
        if self.end_time and self.start_time:
            return (self.end_time - self.start_time).total_seconds()
        return None
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate as fixes validated / issues processed."""
        if self.issues_processed == 0:
            return 0.0
        return self.fixes_validated / self.issues_processed


@dataclass
class ValidationResult:
    """Result of code fix validation."""
    
    is_valid: bool
    syntax_errors: List[str]
    linting_errors: List[str]
    security_warnings: List[str]
    confidence_score: float
    
    @property
    def has_errors(self) -> bool:
        """Check if validation found any errors."""
        return len(self.syntax_errors) > 0 or len(self.linting_errors) > 0
    
    @property
    def all_issues(self) -> List[str]:
        """Get all validation issues combined."""
        return self.syntax_errors + self.linting_errors + self.security_warnings