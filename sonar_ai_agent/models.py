"""
Data models for SonarQube AI Agent.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Any, Dict
from enum import Enum


class IssueType(Enum):
    """SonarQube issue types."""
    BUG = "BUG"
    VULNERABILITY = "VULNERABILITY"
    CODE_SMELL = "CODE_SMELL"


class Severity(Enum):
    """SonarQube issue severities."""
    BLOCKER = "BLOCKER"
    CRITICAL = "CRITICAL"
    MAJOR = "MAJOR"
    MINOR = "MINOR"
    INFO = "INFO"


@dataclass
class SonarIssue:
    """Represents a SonarQube issue."""
    key: str
    rule: str
    severity: str
    message: str
    component: str
    project: str
    type: str
    line: Optional[int] = None
    hash: Optional[str] = None
    text_range: Optional[Dict[str, Any]] = None
    flows: Optional[List[Dict[str, Any]]] = None
    resolution: Optional[str] = None
    status: Optional[str] = None
    creation_date: Optional[str] = None
    update_date: Optional[str] = None
    close_date: Optional[str] = None
    assignee: Optional[str] = None
    author: Optional[str] = None
    comments: Optional[List[Dict[str, Any]]] = None
    tags: Optional[List[str]] = None
    transitions: Optional[List[str]] = None
    actions: Optional[List[str]] = None
    debt: Optional[str] = None
    effort: Optional[str] = None


@dataclass
class FixPlan:
    """Represents a fix plan for a SonarQube issue."""
    issue_key: str
    file_path: str
    line_number: int
    issue_description: str
    problem_analysis: str
    proposed_solution: str
    confidence_score: float
    estimated_effort: str
    potential_side_effects: List[str] = field(default_factory=list)
    fix_type: str = "replace"  # replace, insert, delete, regex
    severity: str = "MINOR"
    created_at: Optional[datetime] = None

    def __post_init__(self):
        """Set created_at if not provided."""
        if self.created_at is None:
            self.created_at = datetime.now()


@dataclass
class AgentMetrics:
    """Metrics tracking for agent performance."""
    agent_name: str
    start_time: datetime
    end_time: Optional[datetime] = None
    processing_time_seconds: float = 0.0
    issues_processed: int = 0
    fixes_applied: int = 0
    success_rate: float = 0.0
    confidence_scores: List[float] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    def add_error(self, error: str):
        """Add an error to the metrics."""
        self.errors.append(error)

    def add_confidence_score(self, score: float):
        """Add a confidence score to the metrics."""
        self.confidence_scores.append(score)

    def calculate_success_rate(self):
        """Calculate and update success rate."""
        if self.issues_processed > 0:
            self.success_rate = self.fixes_applied / self.issues_processed
        else:
            self.success_rate = 0.0


@dataclass
class WorkflowResult:
    """Result from a workflow execution."""
    status: str  # success, error, warning
    message: str
    data: Optional[Dict[str, Any]] = None
    metrics: Optional[AgentMetrics] = None
    timestamp: Optional[datetime] = None

    def __post_init__(self):
        """Set timestamp if not provided."""
        if self.timestamp is None:
            self.timestamp = datetime.now()


@dataclass
class SonarQubeConfig:
    """SonarQube configuration."""
    url: str
    token: str
    project_key: str
    default_severities: List[str] = field(
        default_factory=lambda: ["BLOCKER", "CRITICAL", "MAJOR"])
    default_types: List[str] = field(default_factory=lambda: [
                                     "BUG", "VULNERABILITY", "CODE_SMELL"])


@dataclass
class GitConfig:
    """Git configuration."""
    repo_path: str
    remote_name: str = "origin"
    default_branch: str = "main"
    gitlab_url: Optional[str] = None
    gitlab_token: Optional[str] = None
    project_id: Optional[str] = None
