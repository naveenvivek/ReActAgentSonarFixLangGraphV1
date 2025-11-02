"""
SonarQube AI Agent System

An intelligent code quality automation tool featuring two specialized AI agents:
- Bug Hunter Agent: Connects to SonarQube, analyzes issues, creates fix plans
- Code Healer Agent: Receives fix plans, generates code fixes, creates merge requests

Uses LangGraph workflows with local Ollama LLMs for secure processing.
"""

__version__ = "0.1.0"
__author__ = "SonarQube AI Agent Team"

from .config import Config
from .models import SonarIssue, FixPlan, CodeFix, WorkflowState

__all__ = [
    "Config",
    "SonarIssue", 
    "FixPlan",
    "CodeFix",
    "WorkflowState"
]