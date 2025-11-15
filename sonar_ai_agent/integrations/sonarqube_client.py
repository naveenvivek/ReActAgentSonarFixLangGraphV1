"""
SonarQube client for API integration.
"""

import requests
from typing import List, Optional, Dict, Any
from urllib.parse import urljoin

from ..models import SonarIssue
from ..config import Config


class SonarQubeClient:
    """Client for interacting with SonarQube API."""

    def __init__(self, config: Config):
        """Initialize SonarQube client."""
        self.config = config
        self.base_url = config.sonar_url
        self.token = config.sonar_token

        # Setup session
        self.session = requests.Session()
        self.session.auth = (self.token, '')

    def get_issues(self, project_key: str, severities: List[str] = None, types: List[str] = None) -> List[SonarIssue]:
        """Get issues from SonarQube for a project."""
        try:
            url = urljoin(self.base_url, '/api/issues/search')

            # Use configured max issues limit
            max_issues = getattr(self.config, 'sonar_max_issues', 50)
            timeout = getattr(self.config, 'sonar_request_timeout', 30)

            params = {
                'componentKeys': project_key,
                'ps': max_issues,  # Page size from config
                'p': 1      # Page number
            }

            if severities:
                params['severities'] = ','.join(severities)

            if types:
                params['types'] = ','.join(types)

            response = self.session.get(url, params=params, timeout=timeout)
            response.raise_for_status()

            data = response.json()
            issues_data = data.get('issues', [])

            # Convert to SonarIssue objects
            issues = []
            for issue_data in issues_data:
                issue = self._create_sonar_issue(issue_data)
                if issue:
                    issues.append(issue)

            # Log how many issues were retrieved
            print(
                f"📊 Retrieved {len(issues)} issues (max configured: {max_issues})")
            return issues

        except Exception as e:
            print(f"Error fetching issues from SonarQube: {e}")
            return []

    def get_issue(self, issue_key: str) -> Optional[SonarIssue]:
        """Get a specific issue by key."""
        try:
            url = urljoin(self.base_url, '/api/issues/search')
            params = {'issues': issue_key}

            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()

            data = response.json()
            issues_data = data.get('issues', [])

            if issues_data:
                return self._create_sonar_issue(issues_data[0])

            return None

        except Exception as e:
            print(f"Error fetching issue {issue_key}: {e}")
            return None

    def get_project_info(self, project_key: str) -> Optional[Dict[str, Any]]:
        """Get project information."""
        try:
            url = urljoin(self.base_url, '/api/projects/search')
            params = {'projects': project_key}

            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()

            data = response.json()
            components = data.get('components', [])

            if components:
                return components[0]

            return None

        except Exception as e:
            print(f"Error fetching project info: {e}")
            return None

    def test_connection(self) -> bool:
        """Test connection to SonarQube."""
        try:
            url = urljoin(self.base_url, '/api/system/status')
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            return True
        except Exception:
            return False

    def _create_sonar_issue(self, issue_data: Dict[str, Any]) -> Optional[SonarIssue]:
        """Create SonarIssue object from API response data."""
        try:
            # Extract text range line number
            line = None
            text_range = issue_data.get('textRange')
            if text_range:
                line = text_range.get('startLine')

            return SonarIssue(
                key=issue_data['key'],
                rule=issue_data['rule'],
                severity=issue_data['severity'],
                message=issue_data['message'],
                component=issue_data['component'],
                project=issue_data['project'],
                type=issue_data['type'],
                line=line,
                hash=issue_data.get('hash'),
                text_range=text_range,
                flows=issue_data.get('flows'),
                resolution=issue_data.get('resolution'),
                status=issue_data.get('status'),
                creation_date=issue_data.get('creationDate'),
                update_date=issue_data.get('updateDate'),
                close_date=issue_data.get('closeDate'),
                assignee=issue_data.get('assignee'),
                author=issue_data.get('author'),
                comments=issue_data.get('comments'),
                tags=issue_data.get('tags'),
                transitions=issue_data.get('transitions'),
                actions=issue_data.get('actions'),
                debt=issue_data.get('debt'),
                effort=issue_data.get('effort')
            )

        except KeyError as e:
            print(f"Missing required field in issue data: {e}")
            return None
        except Exception as e:
            print(f"Error creating SonarIssue: {e}")
            return None
