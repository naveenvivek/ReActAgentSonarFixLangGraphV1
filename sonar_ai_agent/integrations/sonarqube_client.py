"""
SonarQube API client for the Bug Hunter Agent.
Handles connection to local SonarQube instance and issue fetching.
"""

import requests
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
import time

from ..config import Config
from ..models import SonarIssue
from ..utils.logger import get_logger


class SonarQubeClient:
    """Client for connecting to SonarQube API and fetching issues."""
    
    def __init__(self, config: Config):
        """Initialize SonarQube client with configuration."""
        self.config = config
        self.base_url = config.sonar_url
        self.token = config.sonar_token
        self.project_key = config.sonar_project_key
        
        # Initialize file-based logger
        self.logger = get_logger(config, "sonar_ai_agent.sonarqube_client")
        
        # Setup session with authentication
        self.session = requests.Session()
        self.session.auth = (self.token, '')  # SonarQube uses token as username, empty password
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
    
    def test_connection(self) -> bool:
        """Test connection to SonarQube server."""
        try:
            api_url = f"{self.base_url}/api/system/status"
            self.logger.info("SonarQube API Call", 
                           api_endpoint="system/status",
                           url=api_url,
                           method="GET")
            
            response = self.session.get(api_url)
            
            if response.status_code == 200:
                status_data = response.json()
                self.logger.info("SonarQube API Response", 
                               api_endpoint="system/status",
                               status_code=response.status_code,
                               sonar_status=status_data.get('status', 'Unknown'),
                               version=status_data.get('version', 'Unknown'))
                return True
            else:
                self.logger.error("SonarQube API Response", 
                                api_endpoint="system/status",
                                status_code=response.status_code,
                                response_text=response.text)
                return False
        except Exception as e:
            self.logger.error(f"Failed to connect to SonarQube: {e}")
            return False
    
    def get_project_info(self, project_key: Optional[str] = None) -> Dict[str, Any]:
        """Get project information from SonarQube."""
        project_key = project_key or self.project_key
        try:
            api_url = f"{self.base_url}/api/projects/search"
            params = {'projects': project_key}
            
            self.logger.info("SonarQube API Call", 
                           api_endpoint="projects/search",
                           url=api_url,
                           params=params)
            
            response = self.session.get(api_url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                projects = data.get('components', [])
                
                self.logger.info("SonarQube API Response", 
                               api_endpoint="projects/search",
                               status_code=response.status_code,
                               projects_found=len(projects))
                
                if projects:
                    project = projects[0]
                    self.logger.info("SonarQube Project Found", 
                                   project_name=project.get('name'),
                                   project_key=project.get('key'),
                                   project_qualifier=project.get('qualifier'))
                    return project
                else:
                    self.logger.warning(f"Project not found: {project_key}")
                    return {}
            else:
                self.logger.error("SonarQube API Response", 
                                api_endpoint="projects/search",
                                status_code=response.status_code,
                                response_text=response.text)
                return {}
                
        except Exception as e:
            self.logger.error(f"Error getting project info: {e}")
            return {}
    
    def fetch_issues(self, project_key: Optional[str] = None, 
                    severities: Optional[List[str]] = None,
                    types: Optional[List[str]] = None,
                    statuses: Optional[List[str]] = None,
                    page_size: int = 100) -> List[SonarIssue]:
        """
        Fetch issues from SonarQube for the specified project.
        
        Args:
            project_key: SonarQube project key (defaults to config value)
            severities: List of severities to filter (BLOCKER, CRITICAL, MAJOR, MINOR, INFO)
            types: List of types to filter (BUG, VULNERABILITY, CODE_SMELL)
            statuses: List of statuses to filter (OPEN, CONFIRMED, REOPENED, RESOLVED, CLOSED)
            page_size: Number of issues per page
            
        Returns:
            List of SonarIssue objects
        """
        project_key = project_key or self.project_key
        
        # Default filters for Bug Hunter Agent
        if severities is None:
            severities = ['BLOCKER', 'CRITICAL', 'MAJOR']  # Focus on high-priority issues
        if types is None:
            types = ['BUG', 'VULNERABILITY', 'CODE_SMELL']
        if statuses is None:
            statuses = ['OPEN', 'CONFIRMED', 'REOPENED']  # Only active issues
        
        try:
            all_issues = []
            page = 1
            
            while True:
                params = {
                    'componentKeys': project_key,
                    'severities': ','.join(severities),
                    'types': ','.join(types),
                    'statuses': ','.join(statuses),
                    'ps': page_size,
                    'p': page
                }
                
                api_url = f"{self.base_url}/api/issues/search"
                self.logger.debug(f"Fetching issues page {page} with params: {params}")
                self.logger.info("SonarQube API Call", 
                               api_endpoint="issues/search",
                               url=api_url,
                               params=params,
                               page=page)
                
                response = self.session.get(api_url, params=params)
                
                if response.status_code == 200:
                    data = response.json()
                    issues = data.get('issues', [])
                    
                    # Log API response details
                    self.logger.info("SonarQube API Response", 
                                   api_endpoint="issues/search",
                                   status_code=response.status_code,
                                   issues_count=len(issues),
                                   total_issues=data.get('paging', {}).get('total', 0),
                                   page=page)
                    
                    if not issues:
                        break  # No more issues
                    
                    # Convert to SonarIssue objects
                    for issue_data in issues:
                        sonar_issue = self._convert_to_sonar_issue(issue_data)
                        if sonar_issue:
                            all_issues.append(sonar_issue)
                            # Log individual issue details
                            self.logger.debug("SonarQube Issue Found", 
                                             issue_key=sonar_issue.key,
                                             severity=sonar_issue.severity,
                                             type=sonar_issue.type,
                                             component=sonar_issue.component,
                                             line=sonar_issue.line,
                                             issue_message=sonar_issue.message)
                    
                    # Check if there are more pages
                    paging = data.get('paging', {})
                    total = paging.get('total', 0)
                    current_count = page * page_size
                    
                    if current_count >= total:
                        break
                    
                    page += 1
                    
                elif response.status_code == 401:
                    self.logger.error("Authentication failed - check SonarQube token")
                    break
                elif response.status_code == 404:
                    self.logger.error(f"Project not found: {project_key}")
                    break
                else:
                    self.logger.error(f"Failed to fetch issues: {response.status_code} - {response.text}")
                    break
            
            self.logger.info(f"Fetched {len(all_issues)} issues from project {project_key}")
            return all_issues
            
        except Exception as e:
            self.logger.error(f"Error fetching issues: {e}")
            return []
    
    def get_issue_details(self, issue_key: str) -> Dict[str, Any]:
        """Get detailed information for a specific issue."""
        try:
            response = self.session.get(
                f"{self.base_url}/api/issues/search",
                params={'issues': issue_key}
            )
            
            if response.status_code == 200:
                data = response.json()
                issues = data.get('issues', [])
                if issues:
                    return issues[0]
            
            self.logger.warning(f"Issue not found: {issue_key}")
            return {}
            
        except Exception as e:
            self.logger.error(f"Error getting issue details: {e}")
            return {}
    
    def get_source_code(self, component_key: str, from_line: int = 1, to_line: int = None) -> str:
        """Get source code for a component (file) from SonarQube."""
        try:
            params = {
                'key': component_key,
                'from': from_line
            }
            if to_line:
                params['to'] = to_line
            
            response = self.session.get(
                f"{self.base_url}/api/sources/show",
                params=params
            )
            
            if response.status_code == 200:
                data = response.json()
                sources = data.get('sources', [])
                return '\n'.join([source.get('code', '') for source in sources])
            else:
                self.logger.warning(f"Could not get source code for {component_key}")
                return ""
                
        except Exception as e:
            self.logger.error(f"Error getting source code: {e}")
            return ""
    
    def _convert_to_sonar_issue(self, issue_data: Dict[str, Any]) -> Optional[SonarIssue]:
        """Convert SonarQube API response to SonarIssue object."""
        try:
            # Parse creation date
            creation_date_str = issue_data.get('creationDate', '')
            creation_date = datetime.fromisoformat(creation_date_str.replace('Z', '+00:00')) if creation_date_str else datetime.now()
            
            return SonarIssue(
                key=issue_data.get('key', ''),
                rule=issue_data.get('rule', ''),
                severity=issue_data.get('severity', ''),
                component=issue_data.get('component', ''),
                line=issue_data.get('line', 0),
                message=issue_data.get('message', ''),
                type=issue_data.get('type', ''),
                status=issue_data.get('status', ''),
                creation_date=creation_date,
                tags=issue_data.get('tags', [])
            )
        except Exception as e:
            self.logger.error(f"Error converting issue data: {e}")
            return None
    
    def get_project_metrics(self, project_key: Optional[str] = None) -> Dict[str, Any]:
        """Get project quality metrics from SonarQube."""
        project_key = project_key or self.project_key
        
        metrics = [
            'bugs', 'vulnerabilities', 'code_smells',
            'coverage', 'duplicated_lines_density',
            'ncloc', 'sqale_index', 'reliability_rating',
            'security_rating', 'sqale_rating'
        ]
        
        try:
            response = self.session.get(
                f"{self.base_url}/api/measures/component",
                params={
                    'component': project_key,
                    'metricKeys': ','.join(metrics)
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                component = data.get('component', {})
                measures = component.get('measures', [])
                
                metrics_dict = {}
                for measure in measures:
                    metric_key = measure.get('metric')
                    value = measure.get('value')
                    metrics_dict[metric_key] = value
                
                self.logger.info(f"Retrieved {len(metrics_dict)} metrics for project {project_key}")
                return metrics_dict
            else:
                self.logger.error(f"Failed to get project metrics: {response.status_code}")
                return {}
                
        except Exception as e:
            self.logger.error(f"Error getting project metrics: {e}")
            return {}
    
    def wait_for_analysis(self, project_key: Optional[str] = None, timeout: int = 300) -> bool:
        """Wait for SonarQube analysis to complete."""
        project_key = project_key or self.project_key
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                response = self.session.get(
                    f"{self.base_url}/api/ce/activity",
                    params={'component': project_key, 'ps': 1}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    tasks = data.get('tasks', [])
                    if tasks:
                        task = tasks[0]
                        status = task.get('status')
                        if status == 'SUCCESS':
                            self.logger.info(f"Analysis completed for project {project_key}")
                            return True
                        elif status == 'FAILED':
                            self.logger.error(f"Analysis failed for project {project_key}")
                            return False
                        else:
                            self.logger.info(f"Analysis in progress: {status}")
                
                time.sleep(10)  # Wait 10 seconds before checking again
                
            except Exception as e:
                self.logger.error(f"Error checking analysis status: {e}")
                return False
        
        self.logger.warning(f"Analysis timeout for project {project_key}")
        return False