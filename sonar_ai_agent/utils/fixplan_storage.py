"""
Fix plan storage utilities for persistent JSON storage.
"""

import json
import os
from typing import List, Optional, Dict, Any
from datetime import datetime
from pathlib import Path

from ..models import FixPlan


class FixPlanStorage:
    """Manages persistent storage of fix plans in JSON format."""

    def __init__(self, base_dir: str = "fixplan"):
        """Initialize fix plan storage."""
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(exist_ok=True)

    def save_fix_plan(self, fix_plan: FixPlan, project_key: str) -> bool:
        """Save a fix plan to persistent storage."""
        try:
            # Convert FixPlan to dictionary
            fix_plan_dict = self._fix_plan_to_dict(fix_plan)

            # Add metadata
            fix_plan_dict["project_key"] = project_key
            fix_plan_dict["stored_at"] = datetime.now().isoformat()

            # Save to single project file
            project_file = self.base_dir / f"{project_key}.json"
            self._append_to_json_file(project_file, fix_plan_dict)

            return True

        except Exception as e:
            print(f"❌ Error saving fix plan {fix_plan.issue_key}: {e}")
            return False

    def load_fix_plan(self, issue_key: str, project_key: str) -> Optional[FixPlan]:
        """Load a specific fix plan by issue key and project."""
        try:
            project_file = self.base_dir / f"{project_key}.json"
            if not project_file.exists():
                return None

            fix_plans = self._load_json_file(project_file)
            for plan_dict in fix_plans:
                if plan_dict.get("issue_key") == issue_key:
                    return self._dict_to_fix_plan(plan_dict)

            return None

        except Exception as e:
            print(f"Error loading fix plan {issue_key}: {e}")
            return None

    def get_fix_plans_by_project(self, project_key: str) -> List[FixPlan]:
        """Get all fix plans for a specific project."""
        try:
            project_file = self.base_dir / f"{project_key}.json"
            if not project_file.exists():
                return []

            fix_plans_dict = self._load_json_file(project_file)
            return [self._dict_to_fix_plan(plan_dict) for plan_dict in fix_plans_dict]

        except Exception as e:
            print(f"❌ Error loading fix plans for project {project_key}: {e}")
            return []

    def get_fix_plans_by_date(self, date_str: str) -> List[FixPlan]:
        """Get all fix plans for a specific date (YYYY-MM-DD)."""
        all_plans = []
        for project in self.list_projects():
            project_plans = self.get_fix_plans_by_project(project)
            for plan in project_plans:
                if plan.created_at and plan.created_at.strftime("%Y-%m-%d") == date_str:
                    all_plans.append(plan)
        return all_plans

    def get_fix_plans_by_severity(self, severity: str) -> List[FixPlan]:
        """Get all fix plans for a specific severity."""
        all_plans = []
        for project in self.list_projects():
            project_plans = self.get_fix_plans_by_project(project)
            for plan in project_plans:
                if plan.severity.lower() == severity.lower():
                    all_plans.append(plan)
        return all_plans

    def list_projects(self) -> List[str]:
        """List all projects with stored fix plans."""
        try:
            projects = []
            for file_path in self.base_dir.glob("*.json"):
                project_key = file_path.stem
                projects.append(project_key)
            return sorted(projects)
        except Exception as e:
            print(f"Error listing projects: {e}")
            return []

    def get_storage_stats(self) -> Dict[str, Any]:
        """Get statistics about stored fix plans."""
        try:
            stats = {
                "total_projects": len(self.list_projects()),
                "by_project": {},
                "by_severity": {},
                "storage_path": str(self.base_dir.absolute())
            }

            # Project stats
            for project in self.list_projects():
                fix_plans = self.get_fix_plans_by_project(project)
                stats["by_project"][project] = len(fix_plans)

            # Severity stats
            severities = ["blocker", "critical", "major", "minor", "info"]
            for severity in severities:
                fix_plans = self.get_fix_plans_by_severity(severity)
                stats["by_severity"][severity] = len(fix_plans)

            return stats

        except Exception as e:
            print(f"Error getting storage stats: {e}")
            return {}

    def archive_project(self, project_key: str) -> bool:
        """Archive fix plans for a project."""
        try:
            project_file = self.by_project_dir / f"{project_key}.json"
            if not project_file.exists():
                return False

            # Move to archive with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            archive_file = self.archive_dir / f"{project_key}_{timestamp}.json"

            project_file.rename(archive_file)
            return True

        except Exception as e:
            print(f"Error archiving project {project_key}: {e}")
            return False

    def _fix_plan_to_dict(self, fix_plan: FixPlan) -> Dict[str, Any]:
        """Convert FixPlan object to dictionary."""
        return {
            "issue_key": fix_plan.issue_key,
            "file_path": fix_plan.file_path,
            "line_number": fix_plan.line_number,
            "issue_description": fix_plan.issue_description,
            "problem_analysis": fix_plan.problem_analysis,
            "proposed_solution": fix_plan.proposed_solution,
            "confidence_score": fix_plan.confidence_score,
            "estimated_effort": fix_plan.estimated_effort,
            "potential_side_effects": fix_plan.potential_side_effects,
            "fix_type": fix_plan.fix_type,
            "severity": fix_plan.severity,
            "created_at": fix_plan.created_at.isoformat() if fix_plan.created_at else None
        }

    def _dict_to_fix_plan(self, plan_dict: Dict[str, Any]) -> FixPlan:
        """Convert dictionary to FixPlan object."""
        created_at = None
        if plan_dict.get("created_at"):
            try:
                created_at = datetime.fromisoformat(plan_dict["created_at"])
            except ValueError:
                created_at = datetime.now()

        return FixPlan(
            issue_key=plan_dict["issue_key"],
            file_path=plan_dict["file_path"],
            line_number=plan_dict["line_number"],
            issue_description=plan_dict["issue_description"],
            problem_analysis=plan_dict["problem_analysis"],
            proposed_solution=plan_dict["proposed_solution"],
            confidence_score=plan_dict["confidence_score"],
            estimated_effort=plan_dict["estimated_effort"],
            potential_side_effects=plan_dict.get("potential_side_effects", []),
            fix_type=plan_dict.get("fix_type", "replace"),
            severity=plan_dict.get("severity", "MINOR"),
            created_at=created_at
        )

    def _append_to_json_file(self, file_path: Path, data: Dict[str, Any]):
        """Append data to JSON file (as array)."""
        if file_path.exists():
            with open(file_path, 'r', encoding='utf-8') as f:
                existing_data = json.load(f)
        else:
            existing_data = []

        existing_data.append(data)

        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(existing_data, f, indent=2, ensure_ascii=False)

    def _load_json_file(self, file_path: Path) -> List[Dict[str, Any]]:
        """Load JSON file as list of dictionaries."""
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
