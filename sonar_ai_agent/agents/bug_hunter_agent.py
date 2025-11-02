"""
Bug Hunter Agent - First agent in the SonarQube AI Agent system.
Connects to SonarQube, fetches issues, analyzes problems, and creates fix plans.
"""

from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import json
from langfuse import observe

from .base_agent import BaseAgent
from ..models import SonarIssue, FixPlan
from ..integrations.sonarqube_client import SonarQubeClient
from ..integrations.git_client import GitClient


class BugHunterAgent(BaseAgent):
    """
    Bug Hunter Agent responsible for:
    1. Connecting to SonarQube and fetching issues
    2. Analyzing code problems using Ollama LLM
    3. Creating structured fix plans for the Code Healer Agent
    """
    
    def __init__(self, config):
        """Initialize Bug Hunter Agent."""
        super().__init__(config, "BugHunterAgent")
        
        # Initialize clients
        self.sonar_client = SonarQubeClient(config)
        self.git_client = GitClient(config)
        
        # Agent-specific configuration
        self.max_issues_per_run = 10  # Limit for initial processing
        self.context_lines = 15  # Lines of code context around issues
        
        self.logger.info("Bug Hunter Agent initialized")
    
    @observe(name="bug_hunter_process")
    def process(self, project_key: Optional[str] = None, 
                severities: Optional[List[str]] = None,
                issue_types: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Main processing method for Bug Hunter Agent.
        
        Args:
            project_key: SonarQube project key (optional, uses config default)
            severities: List of severities to process (optional)
            issue_types: List of issue types to process (optional)
            
        Returns:
            Dictionary containing processing results and fix plans
        """
        self.start_metrics_tracking()
        
        try:
            self.logger.info("Starting Bug Hunter Agent processing")
            
            # Step 1: Ensure repository is available
            if not self._prepare_repository():
                return self._create_error_result("Failed to prepare repository")
            
            # Step 2: Connect to SonarQube and validate connection
            if not self._validate_sonar_connection():
                return self._create_error_result("Failed to connect to SonarQube")
            
            # Step 3: Fetch issues from SonarQube
            issues = self._fetch_sonar_issues(project_key, severities, issue_types)
            if not issues:
                return self._create_success_result([], "No issues found to process")
            
            # Step 4: Prioritize issues for processing
            prioritized_issues = self._prioritize_issues(issues)
            
            # Step 5: Analyze issues and create fix plans
            fix_plans = []
            for issue in prioritized_issues[:self.max_issues_per_run]:
                fix_plan = self._analyze_issue_and_create_plan(issue)
                if fix_plan:
                    fix_plans.append(fix_plan)
            
            # Step 6: Create processing summary
            result = self._create_success_result(fix_plans, f"Processed {len(fix_plans)} issues")
            
            self.logger.info(f"Bug Hunter Agent completed: {len(fix_plans)} fix plans created")
            return result
            
        except Exception as e:
            self.log_error(e, "Bug Hunter Agent processing failed")
            return self._create_error_result(f"Processing failed: {str(e)}")
        
        finally:
            metrics = self.stop_metrics_tracking()
            if metrics:
                self.create_langfuse_score(
                    "bug_hunter_processing_time",
                    metrics.processing_time_seconds,
                    f"Processing time for {len(fix_plans) if 'fix_plans' in locals() else 0} issues"
                )
    
    def _prepare_repository(self) -> bool:
        """Ensure the target repository is cloned and up to date."""
        try:
            self.logger.info("Preparing target repository")
            
            # Clone or update repository
            if not self.git_client.clone_repository():
                self.logger.error("Failed to clone/update repository")
                return False
            
            # Verify repository info
            repo_info = self.git_client.get_repository_info()
            self.logger.info(f"Repository ready: {repo_info.get('remote_url', 'Unknown')}")
            
            return True
            
        except Exception as e:
            self.log_error(e, "Repository preparation failed")
            return False
    
    def _validate_sonar_connection(self) -> bool:
        """Validate connection to SonarQube server."""
        try:
            self.logger.info("Validating SonarQube connection")
            
            if not self.sonar_client.test_connection():
                return False
            
            # Verify project exists
            project_info = self.sonar_client.get_project_info()
            if not project_info:
                self.logger.error(f"Project not found: {self.config.sonar_project_key}")
                return False
            
            self.logger.info(f"Connected to project: {project_info.get('name', 'Unknown')}")
            return True
            
        except Exception as e:
            self.log_error(e, "SonarQube connection validation failed")
            return False
    
    def _fetch_sonar_issues(self, project_key: Optional[str] = None,
                           severities: Optional[List[str]] = None,
                           issue_types: Optional[List[str]] = None) -> List[SonarIssue]:
        """Fetch issues from SonarQube."""
        try:
            self.logger.info("Fetching issues from SonarQube")
            
            # Use defaults if not specified
            if severities is None:
                severities = ['BLOCKER', 'CRITICAL', 'MAJOR']
            if issue_types is None:
                issue_types = ['BUG', 'VULNERABILITY', 'CODE_SMELL']
            
            issues = self.sonar_client.fetch_issues(
                project_key=project_key,
                severities=severities,
                types=issue_types
            )
            
            self.logger.info(f"Fetched {len(issues)} issues from SonarQube")
            return issues
            
        except Exception as e:
            self.log_error(e, "Failed to fetch SonarQube issues")
            return []
    
    def _prioritize_issues(self, issues: List[SonarIssue]) -> List[SonarIssue]:
        """
        Prioritize issues based on severity, type, and other factors.
        
        Priority order:
        1. BLOCKER bugs and vulnerabilities
        2. CRITICAL bugs and vulnerabilities  
        3. MAJOR bugs and vulnerabilities
        4. MAJOR code smells
        5. Others
        """
        try:
            self.logger.info(f"Prioritizing {len(issues)} issues")
            
            def priority_score(issue: SonarIssue) -> int:
                score = 0
                
                # Severity scoring
                severity_scores = {
                    'BLOCKER': 1000,
                    'CRITICAL': 800,
                    'MAJOR': 600,
                    'MINOR': 400,
                    'INFO': 200
                }
                score += severity_scores.get(issue.severity, 0)
                
                # Type scoring
                type_scores = {
                    'BUG': 300,
                    'VULNERABILITY': 250,
                    'CODE_SMELL': 100
                }
                score += type_scores.get(issue.type, 0)
                
                # Newer issues get slight priority (handle timezone-aware dates)
                try:
                    if issue.creation_date.tzinfo is not None:
                        # Convert to naive datetime for comparison
                        creation_date = issue.creation_date.replace(tzinfo=None)
                    else:
                        creation_date = issue.creation_date
                    days_old = (datetime.now() - creation_date).days
                    score += max(0, 30 - days_old)  # Bonus for issues less than 30 days old
                except (AttributeError, TypeError):
                    # If date parsing fails, skip the age bonus
                    pass
                
                return score
            
            # Sort by priority score (highest first)
            prioritized = sorted(issues, key=priority_score, reverse=True)
            
            self.logger.info(f"Issues prioritized - Top issue: {prioritized[0].severity} {prioritized[0].type}")
            return prioritized
            
        except Exception as e:
            self.log_error(e, "Issue prioritization failed")
            return issues  # Return original list if prioritization fails
    
    @observe(name="analyze_issue_and_create_plan")
    def _analyze_issue_and_create_plan(self, issue: SonarIssue) -> Optional[FixPlan]:
        """
        Analyze a single issue and create a fix plan using Ollama LLM.
        
        Args:
            issue: SonarIssue to analyze
            
        Returns:
            FixPlan object or None if analysis fails
        """
        try:
            self.logger.info(f"Analyzing issue: {issue.key} - {issue.message}")
            
            # Step 1: Get code context
            code_context = self._get_code_context(issue)
            if not code_context:
                self.logger.warning(f"Could not get code context for issue {issue.key}")
                return None
            
            # Step 2: Analyze issue with LLM
            analysis = self._analyze_issue_with_llm(issue, code_context)
            if not analysis:
                self.logger.warning(f"LLM analysis failed for issue {issue.key}")
                return None
            
            # Step 3: Create fix plan
            fix_plan = self._create_fix_plan(issue, code_context, analysis)
            
            if fix_plan:
                self.logger.info(f"Created fix plan for issue {issue.key}")
                self.create_langfuse_score(
                    "fix_plan_confidence",
                    fix_plan.confidence_score,
                    f"Confidence score for issue {issue.key}"
                )
            
            return fix_plan
            
        except Exception as e:
            self.log_error(e, f"Failed to analyze issue {issue.key}")
            return None
    
    def _get_code_context(self, issue: SonarIssue) -> Optional[Dict[str, Any]]:
        """Get code context around the issue location."""
        try:
            # Extract file path from component
            # SonarQube component format: "project_key:file_path"
            if ':' in issue.component:
                file_path = issue.component.split(':', 1)[1]
            else:
                file_path = issue.component
            
            # Get code context from Git repository
            context = self.git_client.get_file_context(
                file_path=file_path,
                target_line=issue.line,
                context_lines=self.context_lines
            )
            
            if context:
                self.logger.debug(f"Got code context for {file_path}:{issue.line}")
                return context
            else:
                # Fallback: try to get from SonarQube
                source_code = self.sonar_client.get_source_code(
                    issue.component,
                    max(1, issue.line - self.context_lines),
                    issue.line + self.context_lines
                )
                
                if source_code:
                    return {
                        'file_path': file_path,
                        'target_line': issue.line,
                        'context_content': source_code,
                        'language': self.git_client._detect_language(file_path)
                    }
            
            return None
            
        except Exception as e:
            self.log_error(e, f"Failed to get code context for issue {issue.key}")
            return None
    
    @observe(name="analyze_issue_with_llm")
    def _analyze_issue_with_llm(self, issue: SonarIssue, code_context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Use Ollama LLM to analyze the issue and understand the problem."""
        try:
            # Create analysis prompt
            system_prompt = self._create_analysis_system_prompt()
            user_prompt = self._create_analysis_user_prompt(issue, code_context)
            
            # Generate analysis using Ollama
            response = self.generate_response(
                prompt=user_prompt,
                system_prompt=system_prompt,
                temperature=0.3,  # Lower temperature for more focused analysis
                max_tokens=1500
            )
            
            # Parse the response
            analysis = self._parse_llm_analysis(response)
            
            if analysis:
                self.logger.debug(f"LLM analysis completed for issue {issue.key}")
                return analysis
            else:
                self.logger.warning(f"Could not parse LLM analysis for issue {issue.key}")
                return None
                
        except Exception as e:
            self.log_error(e, f"LLM analysis failed for issue {issue.key}")
            return None
    
    def _create_analysis_system_prompt(self) -> str:
        """Create system prompt for issue analysis."""
        return """You are an expert code analyst specializing in Java and Spring Boot applications. 
Your task is to analyze SonarQube code quality issues and provide detailed technical analysis.

For each issue, provide:
1. Problem Analysis: What exactly is wrong and why it's a problem
2. Root Cause: The underlying cause of the issue
3. Impact Assessment: How this affects code quality, performance, or security
4. Solution Strategy: High-level approach to fix the issue
5. Side Effects: Potential impacts of the proposed fix
6. Confidence Level: Your confidence in the analysis (0.0 to 1.0)

Respond in JSON format with these keys: problem_analysis, root_cause, impact_assessment, solution_strategy, side_effects, confidence_level.

Focus on practical, actionable insights for Java/Spring Boot development."""
    
    def _create_analysis_user_prompt(self, issue: SonarIssue, code_context: Dict[str, Any]) -> str:
        """Create user prompt with issue and code context."""
        return f"""Analyze this SonarQube issue:

**Issue Details:**
- Key: {issue.key}
- Rule: {issue.rule}
- Severity: {issue.severity}
- Type: {issue.type}
- Message: {issue.message}
- File: {code_context.get('file_path', 'Unknown')}
- Line: {issue.line}
- Language: {code_context.get('language', 'Unknown')}

**Code Context (around line {issue.line}):**
```{code_context.get('language', 'text')}
{code_context.get('context_content', 'No context available')}
```

**Target Line Content:**
```{code_context.get('language', 'text')}
{code_context.get('target_content', 'No content available')}
```

Please analyze this issue and provide your assessment in JSON format."""
    
    def _parse_llm_analysis(self, response: str) -> Optional[Dict[str, Any]]:
        """Parse LLM response into structured analysis."""
        try:
            # Try to extract JSON from response
            response = response.strip()
            
            # Look for JSON block
            if '```json' in response:
                start = response.find('```json') + 7
                end = response.find('```', start)
                json_str = response[start:end].strip()
            elif response.startswith('{') and response.endswith('}'):
                json_str = response
            else:
                # Try to find JSON-like content
                import re
                json_match = re.search(r'\{.*\}', response, re.DOTALL)
                if json_match:
                    json_str = json_match.group()
                else:
                    return None
            
            # Parse JSON
            analysis = json.loads(json_str)
            
            # Validate required fields
            required_fields = ['problem_analysis', 'solution_strategy', 'confidence_level']
            if all(field in analysis for field in required_fields):
                # Ensure confidence_level is a float
                try:
                    if isinstance(analysis['confidence_level'], dict):
                        # If it's a dict, try to extract a numeric value
                        confidence = analysis['confidence_level'].get('value', 0.5)
                    else:
                        confidence = float(analysis['confidence_level'])
                    analysis['confidence_level'] = max(0.0, min(1.0, confidence))  # Clamp between 0 and 1
                except (ValueError, TypeError):
                    analysis['confidence_level'] = 0.5  # Default confidence
                return analysis
            else:
                self.logger.warning("LLM analysis missing required fields")
                return None
                
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse LLM analysis JSON: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Error parsing LLM analysis: {e}")
            return None
    
    def _create_fix_plan(self, issue: SonarIssue, code_context: Dict[str, Any], 
                        analysis: Dict[str, Any]) -> Optional[FixPlan]:
        """Create a structured fix plan from the analysis."""
        try:
            # Extract file path
            if ':' in issue.component:
                file_path = issue.component.split(':', 1)[1]
            else:
                file_path = issue.component
            
            # Create fix plan
            fix_plan = FixPlan(
                issue_key=issue.key,
                issue_description=f"{issue.severity} {issue.type}: {issue.message}",
                file_path=file_path,
                line_number=issue.line,
                problem_analysis=analysis.get('problem_analysis', ''),
                proposed_solution=analysis.get('solution_strategy', ''),
                code_context=code_context.get('context_content', ''),
                potential_side_effects=analysis.get('side_effects', []) if isinstance(analysis.get('side_effects'), list) else [str(analysis.get('side_effects', ''))],
                confidence_score=float(analysis.get('confidence_level', 0.5)),
                estimated_effort=self._estimate_effort(issue, analysis)
            )
            
            return fix_plan
            
        except Exception as e:
            self.log_error(e, f"Failed to create fix plan for issue {issue.key}")
            return None
    
    def _estimate_effort(self, issue: SonarIssue, analysis: Dict[str, Any]) -> str:
        """Estimate effort required to fix the issue."""
        try:
            # Simple effort estimation based on severity and type
            if issue.severity in ['BLOCKER', 'CRITICAL']:
                if issue.type == 'VULNERABILITY':
                    return 'HIGH'
                else:
                    return 'MEDIUM'
            elif issue.severity == 'MAJOR':
                if issue.type == 'BUG':
                    return 'MEDIUM'
                else:
                    return 'LOW'
            else:
                return 'LOW'
                
        except Exception:
            return 'MEDIUM'
    
    def _create_success_result(self, fix_plans: List[FixPlan], message: str) -> Dict[str, Any]:
        """Create successful processing result."""
        return {
            'status': 'success',
            'message': message,
            'fix_plans': fix_plans,
            'total_plans': len(fix_plans),
            'agent': 'BugHunterAgent',
            'timestamp': datetime.now().isoformat()
        }
    
    def _create_error_result(self, error_message: str) -> Dict[str, Any]:
        """Create error processing result."""
        return {
            'status': 'error',
            'message': error_message,
            'fix_plans': [],
            'total_plans': 0,
            'agent': 'BugHunterAgent',
            'timestamp': datetime.now().isoformat()
        }
    
    def get_project_summary(self, project_key: Optional[str] = None) -> Dict[str, Any]:
        """Get a summary of the project's code quality status."""
        try:
            project_key = project_key or self.config.sonar_project_key
            
            # Get project metrics
            metrics = self.sonar_client.get_project_metrics(project_key)
            
            # Get issue counts by severity
            all_issues = self.sonar_client.fetch_issues(
                project_key=project_key,
                severities=['BLOCKER', 'CRITICAL', 'MAJOR', 'MINOR', 'INFO'],
                types=['BUG', 'VULNERABILITY', 'CODE_SMELL']
            )
            
            # Categorize issues
            issue_summary = {
                'total_issues': len(all_issues),
                'by_severity': {},
                'by_type': {}
            }
            
            for issue in all_issues:
                # Count by severity
                severity = issue.severity
                issue_summary['by_severity'][severity] = issue_summary['by_severity'].get(severity, 0) + 1
                
                # Count by type
                issue_type = issue.type
                issue_summary['by_type'][issue_type] = issue_summary['by_type'].get(issue_type, 0) + 1
            
            return {
                'project_key': project_key,
                'metrics': metrics,
                'issues': issue_summary,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.log_error(e, "Failed to get project summary")
            return {}
    
    def __repr__(self) -> str:
        """String representation of Bug Hunter Agent."""
        return f"BugHunterAgent(project={self.config.sonar_project_key}, model={self.config.ollama_model})"