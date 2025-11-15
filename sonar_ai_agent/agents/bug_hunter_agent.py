"""
Bug Hunter Agent - Analyzes SonarQube issues and generates fix plans.
Implements issue analysis, code inspection, and fix plan generation.
"""

import os
import json
import time
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
import requests

from ..models import SonarIssue, FixPlan, AgentMetrics
from ..config import Config
from ..utils.logger import get_logger
from ..integrations.sonarqube_client import SonarQubeClient


class BugHunterAgent:
    """Agent responsible for analyzing SonarQube issues and generating fix plans."""

    def __init__(self, config: Config):
        """Initialize Bug Hunter Agent."""
        self.config = config

        # Initialize file-based logger
        self.logger = get_logger(config, "sonar_ai_agent.bug_hunter_agent")

        # Initialize SonarQube client
        self.sonar_client = SonarQubeClient(config)

        # Metrics tracking
        self.metrics = None
        self.start_time = None

        # AI/LLM configuration (if using Bedrock or other AI services)
        self.use_ai_analysis = config.use_ai_analysis if hasattr(
            config, 'use_ai_analysis') else True

    def analyze_issue(self, issue: SonarIssue) -> Dict[str, Any]:
        """Analyze a single SonarQube issue."""
        self.logger.info(f"🔍 Analyzing issue: {issue.key}")

        start_time = time.time()

        try:
            # Get source code context
            source_context = self._get_source_context(issue)
            if not source_context:
                return {
                    "success": False,
                    "error": f"Could not retrieve source context for issue {issue.key}",
                    "issue_key": issue.key
                }

            # Analyze the issue with AI or rule-based approach
            analysis_result = self._perform_issue_analysis(
                issue, source_context)

            # Calculate processing time
            processing_time = time.time() - start_time

            result = {
                "success": True,
                "issue_key": issue.key,
                "analysis": analysis_result,
                "source_context": source_context,
                "processing_time": processing_time,
                "confidence_score": analysis_result.get("confidence", 0.0)
            }

            self.logger.info(f"✅ Successfully analyzed issue: {issue.key}")
            return result

        except Exception as e:
            self.logger.error(f"❌ Exception analyzing issue {issue.key}: {e}")
            return {
                "success": False,
                "error": str(e),
                "issue_key": issue.key
            }

    def generate_fix_plan(self, issue: SonarIssue) -> Optional[FixPlan]:
        """Generate a fix plan for a SonarQube issue."""
        self.logger.info(f"🛠️ Generating fix plan for issue: {issue.key}")

        try:
            # Get source code context
            source_context = self._get_source_context(issue)
            if not source_context:
                self.logger.error(
                    f"❌ Could not get source context for issue: {issue.key}")
                return None

            # Generate fix plan using AI or rule-based approach
            fix_plan_data = self._generate_fix_plan_data(issue, source_context)
            if not fix_plan_data:
                self.logger.error(
                    f"❌ Could not generate fix plan data for issue: {issue.key}")
                return None

            # Create FixPlan object
            fix_plan = FixPlan(
                issue_key=issue.key,
                file_path=issue.component.replace(f"{issue.project}:", ""),
                line_number=getattr(issue, 'line', 1),
                issue_description=issue.message,
                problem_analysis=fix_plan_data.get("analysis", ""),
                proposed_solution=fix_plan_data.get("solution", ""),
                confidence_score=fix_plan_data.get("confidence", 0.5),
                estimated_effort=fix_plan_data.get("effort", "Medium"),
                potential_side_effects=fix_plan_data.get("side_effects", []),
                fix_type=fix_plan_data.get("fix_type", "replace"),
                severity=getattr(issue, 'severity', 'MINOR'),
                created_at=datetime.now()
            )

            self.logger.info(f"✅ Generated fix plan for issue: {issue.key}")
            return fix_plan

        except Exception as e:
            self.logger.error(
                f"❌ Exception generating fix plan for {issue.key}: {e}")
            return None

    def start_metrics_tracking(self):
        """Start tracking metrics for the Bug Hunter session."""
        self.start_time = time.time()
        self.metrics = AgentMetrics(
            agent_name="BugHunterAgent",
            start_time=datetime.now(),
            end_time=None,
            processing_time_seconds=0,
            issues_processed=0,
            fixes_applied=0,
            success_rate=0.0,
            confidence_scores=[],
            errors=[]
        )
        self.logger.info("📊 Started metrics tracking for Bug Hunter")

    def stop_metrics_tracking(self) -> Optional[AgentMetrics]:
        """Stop metrics tracking and return results."""
        if self.metrics and self.start_time:
            self.metrics.end_time = datetime.now()
            self.metrics.processing_time_seconds = time.time() - self.start_time
            self.logger.info("📊 Stopped metrics tracking for Bug Hunter")
            return self.metrics
        return None

    def _get_source_context(self, issue: SonarIssue) -> Optional[Dict[str, Any]]:
        """Get source code context for the issue."""
        try:
            # Get the file path from the component
            file_path = issue.component.replace(f"{issue.project}:", "")

            # Try to read the file locally first
            local_file_path = os.path.join(os.getcwd(), file_path)
            if os.path.exists(local_file_path):
                with open(local_file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                lines = content.split('\n')
                line_number = getattr(issue, 'line', 1)

                # Get context around the issue line
                start_line = max(0, line_number - 5)
                end_line = min(len(lines), line_number + 5)

                context = {
                    "file_path": file_path,
                    "line_number": line_number,
                    "issue_line": lines[line_number - 1] if line_number <= len(lines) else "",
                    "context_lines": lines[start_line:end_line],
                    "full_content": content,
                    "source": "local_file"
                }

                return context

            # Fallback to SonarQube API for source code
            return self._get_source_from_sonarqube(issue)

        except Exception as e:
            self.logger.error(
                f"❌ Error getting source context for {issue.key}: {e}")
            return None

    def _get_source_from_sonarqube(self, issue: SonarIssue) -> Optional[Dict[str, Any]]:
        """Get source code from SonarQube API."""
        try:
            # This would require SonarQube API integration
            # For now, return a basic context structure
            file_path = issue.component.replace(f"{issue.project}:", "")

            context = {
                "file_path": file_path,
                "line_number": getattr(issue, 'line', 1),
                "issue_line": "// Source code not available locally",
                "context_lines": ["// Context not available"],
                "full_content": "// Full content not available",
                "source": "sonarqube_api"
            }

            return context

        except Exception as e:
            self.logger.error(
                f"❌ Error getting source from SonarQube for {issue.key}: {e}")
            return None

    def _perform_issue_analysis(self, issue: SonarIssue, source_context: Dict[str, Any]) -> Dict[str, Any]:
        """Perform detailed analysis of the issue."""
        if self.use_ai_analysis:
            return self._ai_analyze_issue(issue, source_context)
        else:
            return self._rule_based_analyze_issue(issue, source_context)

    def _ai_analyze_issue(self, issue: SonarIssue, source_context: Dict[str, Any]) -> Dict[str, Any]:
        """Use AI (like AWS Bedrock) to analyze the issue."""
        try:
            # This would integrate with your AI service (AWS Bedrock, etc.)
            # For now, providing a structured analysis

            analysis = {
                "issue_type": issue.type,
                "severity": getattr(issue, 'severity', 'MINOR'),
                "category": self._categorize_issue(issue),
                "root_cause": self._identify_root_cause(issue, source_context),
                "impact_assessment": self._assess_impact(issue),
                "confidence": self._calculate_confidence(issue, source_context),
                "complexity": self._assess_complexity(issue),
                "priority": self._calculate_priority(issue)
            }

            return analysis

        except Exception as e:
            self.logger.error(f"❌ AI analysis failed for {issue.key}: {e}")
            return self._rule_based_analyze_issue(issue, source_context)

    def _rule_based_analyze_issue(self, issue: SonarIssue, source_context: Dict[str, Any]) -> Dict[str, Any]:
        """Use rule-based approach to analyze the issue."""
        try:
            analysis = {
                "issue_type": issue.type,
                "severity": getattr(issue, 'severity', 'MINOR'),
                "category": self._categorize_issue(issue),
                "root_cause": f"SonarQube rule violation: {issue.rule}",
                "impact_assessment": "Medium - affects code quality",
                "confidence": 0.7,  # Default confidence for rule-based
                "complexity": "Medium",
                "priority": "Normal"
            }

            return analysis

        except Exception as e:
            self.logger.error(
                f"❌ Rule-based analysis failed for {issue.key}: {e}")
            return {
                "issue_type": "UNKNOWN",
                "severity": "MINOR",
                "category": "general",
                "root_cause": "Analysis failed",
                "impact_assessment": "Unknown",
                "confidence": 0.3,
                "complexity": "Unknown",
                "priority": "Low"
            }

    def _generate_fix_plan_data(self, issue: SonarIssue, source_context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Generate fix plan data for the issue."""
        try:
            if self.use_ai_analysis:
                return self._ai_generate_fix_plan(issue, source_context)
            else:
                return self._rule_based_generate_fix_plan(issue, source_context)

        except Exception as e:
            self.logger.error(
                f"❌ Fix plan generation failed for {issue.key}: {e}")
            return None

    def _ai_generate_fix_plan(self, issue: SonarIssue, source_context: Dict[str, Any]) -> Dict[str, Any]:
        """Use AI to generate comprehensive fix plan."""
        # This would integrate with your AI service
        # For now, providing a structured approach

        rule_fixes = self._get_rule_based_fixes()
        rule_key = issue.rule

        if rule_key in rule_fixes:
            base_fix = rule_fixes[rule_key]

            # Enhance with AI analysis
            fix_plan = {
                "analysis": f"AI Analysis: {base_fix['description']}",
                "solution": base_fix['solution'],
                # AI boost
                "confidence": min(0.9, base_fix['confidence'] + 0.2),
                "effort": base_fix['effort'],
                "side_effects": base_fix.get('side_effects', []),
                "fix_type": base_fix.get('fix_type', 'replace')
            }
        else:
            # Generic AI-based fix plan
            fix_plan = {
                "analysis": f"AI Analysis of {issue.type} issue in {source_context['file_path']}",
                "solution": f"Recommended fix for rule {issue.rule}",
                "confidence": 0.6,
                "effort": "Medium",
                "side_effects": ["Review recommended before applying"],
                "fix_type": "replace"
            }

        return fix_plan

    def _rule_based_generate_fix_plan(self, issue: SonarIssue, source_context: Dict[str, Any]) -> Dict[str, Any]:
        """Use rule-based approach to generate fix plan."""
        rule_fixes = self._get_rule_based_fixes()
        rule_key = issue.rule

        if rule_key in rule_fixes:
            return rule_fixes[rule_key]
        else:
            # Generic fix plan for unknown rules
            return {
                "analysis": f"Standard fix for {issue.type} issue",
                "solution": f"Apply recommended fix for rule {issue.rule}",
                "confidence": 0.5,
                "effort": "Medium",
                "side_effects": [],
                "fix_type": "replace"
            }

    def _get_rule_based_fixes(self) -> Dict[str, Dict[str, Any]]:
        """Get predefined fixes for common SonarQube rules."""
        return {
            "python:S125": {
                "description": "Remove commented out code",
                "solution": "Delete commented code blocks",
                "confidence": 0.8,
                "effort": "Low",
                "side_effects": [],
                "fix_type": "delete"
            },
            "python:S1481": {
                "description": "Remove unused variables",
                "solution": "Delete unused variable declarations",
                "confidence": 0.9,
                "effort": "Low",
                "side_effects": [],
                "fix_type": "delete"
            },
            "python:S1854": {
                "description": "Remove unused assignments",
                "solution": "Delete unused variable assignments",
                "confidence": 0.8,
                "effort": "Low",
                "side_effects": [],
                "fix_type": "delete"
            },
            "python:S101": {
                "description": "Rename class to follow naming convention",
                "solution": "Use PascalCase for class names",
                "confidence": 0.7,
                "effort": "Medium",
                "side_effects": ["Update all references to the class"],
                "fix_type": "replace"
            },
            "python:S103": {
                "description": "Split long lines",
                "solution": "Break line into multiple lines",
                "confidence": 0.6,
                "effort": "Low",
                "side_effects": [],
                "fix_type": "replace"
            }
        }

    def _categorize_issue(self, issue: SonarIssue) -> str:
        """Categorize the issue based on type and rule."""
        if issue.type == "BUG":
            return "bug"
        elif issue.type == "VULNERABILITY":
            return "security"
        elif issue.type == "CODE_SMELL":
            if "naming" in issue.rule.lower():
                return "naming"
            elif "complexity" in issue.rule.lower():
                return "complexity"
            else:
                return "maintainability"
        else:
            return "general"

    def _identify_root_cause(self, issue: SonarIssue, source_context: Dict[str, Any]) -> str:
        """Identify the root cause of the issue."""
        return f"SonarQube rule violation: {issue.rule} - {issue.message}"

    def _assess_impact(self, issue: SonarIssue) -> str:
        """Assess the impact of the issue."""
        severity = getattr(issue, 'severity', 'MINOR')
        impact_map = {
            'BLOCKER': 'Critical - blocks development',
            'CRITICAL': 'High - major functionality affected',
            'MAJOR': 'Medium - notable impact on quality',
            'MINOR': 'Low - minor quality issue',
            'INFO': 'Informational - no functional impact'
        }
        return impact_map.get(severity, 'Unknown impact')

    def _calculate_confidence(self, issue: SonarIssue, source_context: Dict[str, Any]) -> float:
        """Calculate confidence score for the analysis."""
        confidence = 0.5  # Base confidence

        # Boost confidence for well-known rules
        well_known_rules = ["python:S125", "python:S1481", "python:S1854"]
        if issue.rule in well_known_rules:
            confidence += 0.3

        # Boost confidence if we have good source context
        if source_context.get("source") == "local_file":
            confidence += 0.2

        return min(1.0, confidence)

    def _assess_complexity(self, issue: SonarIssue) -> str:
        """Assess the complexity of fixing the issue."""
        if issue.type == "CODE_SMELL":
            return "Low"
        elif issue.type == "BUG":
            return "Medium"
        elif issue.type == "VULNERABILITY":
            return "High"
        else:
            return "Medium"

    def _calculate_priority(self, issue: SonarIssue) -> str:
        """Calculate priority for fixing the issue."""
        severity = getattr(issue, 'severity', 'MINOR')
        priority_map = {
            'BLOCKER': 'Critical',
            'CRITICAL': 'High',
            'MAJOR': 'Medium',
            'MINOR': 'Low',
            'INFO': 'Low'
        }
        return priority_map.get(severity, 'Normal')

    def get_agent_info(self) -> Dict[str, Any]:
        """Get information about the Bug Hunter Agent."""
        return {
            "agent_name": "BugHunterAgent",
            "version": "1.0.0",
            "capabilities": [
                "SonarQube issue analysis",
                "Fix plan generation",
                "Source code inspection",
                "AI-powered analysis",
                "Rule-based fixes",
                "Metrics tracking"
            ],
            "supported_languages": ["Python", "Java", "JavaScript", "TypeScript"],
            "ai_analysis_enabled": self.use_ai_analysis,
            "integration": "SonarQube API"
        }
