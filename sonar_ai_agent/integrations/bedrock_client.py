"""
AWS Bedrock client for AI-powered code analysis and fix suggestions.
"""

import json
import boto3
from typing import Dict, List, Any, Optional
from botocore.exceptions import ClientError, NoCredentialsError

from ..config import Config
from ..models import SonarIssue


class BedrockClient:
    """Client for interacting with AWS Bedrock AI models."""

    def __init__(self, config: Config):
        """Initialize Bedrock client."""
        self.config = config
        self.model_id = config.bedrock_model_id
        self.region = config.bedrock_region

        try:
            # Initialize Bedrock client
            self.bedrock = boto3.client(
                'bedrock-runtime',
                region_name=self.region,
                aws_access_key_id=config.aws_access_key_id,
                aws_secret_access_key=config.aws_secret_access_key
            )
            self.is_available = True
        except (NoCredentialsError, ClientError) as e:
            print(f"⚠️ Bedrock client initialization failed: {e}")
            self.bedrock = None
            self.is_available = False

    def analyze_issue(self, issue: SonarIssue, source_context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Analyze a SonarQube issue using AI."""
        if not self.is_available:
            return None

        try:
            prompt = self._create_analysis_prompt(issue, source_context)
            response = self._invoke_model(prompt)

            if response:
                return self._parse_analysis_response(response)

        except Exception as e:
            print(f"❌ Bedrock analysis failed for {issue.key}: {e}")

        return None

    def generate_fix_plan(self, issue: SonarIssue, source_context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Generate a fix plan using AI."""
        if not self.is_available:
            return None

        try:
            prompt = self._create_fix_plan_prompt(issue, source_context)
            response = self._invoke_model(prompt)

            if response:
                return self._parse_fix_plan_response(response)

        except Exception as e:
            print(f"❌ Bedrock fix plan generation failed for {issue.key}: {e}")

        return None

    def _create_analysis_prompt(self, issue: SonarIssue, source_context: Dict[str, Any]) -> str:
        """Create prompt for issue analysis."""
        file_path = source_context.get('file_path', 'unknown')
        issue_line = source_context.get('issue_line', '')
        context_lines = source_context.get('context_lines', [])

        context_code = '\n'.join(
            [f"{i+1}: {line}" for i, line in enumerate(context_lines)])

        prompt = f"""
You are an expert code analysis AI. Analyze this SonarQube issue and provide detailed insights.

**Issue Details:**
- Rule: {issue.rule}
- Type: {issue.type}
- Severity: {getattr(issue, 'severity', 'UNKNOWN')}
- Message: {issue.message}
- File: {file_path}
- Line: {getattr(issue, 'line', 'unknown')}

**Code Context:**
```
{context_code}
```

**Problem Line:**
{issue_line}

Please provide a JSON response with this structure:
{{
    "root_cause": "Brief explanation of what's causing this issue",
    "impact_assessment": "Description of the impact on code quality/security/functionality",
    "category": "One of: security, performance, maintainability, reliability, naming, complexity",
    "confidence": 0.85,
    "complexity": "Low|Medium|High",
    "priority": "Critical|High|Medium|Low",
    "technical_details": "Technical explanation of the issue"
}}

Focus on accuracy and practical insights. Be concise but thorough.
"""
        return prompt

    def _create_fix_plan_prompt(self, issue: SonarIssue, source_context: Dict[str, Any]) -> str:
        """Create prompt for fix plan generation."""
        file_path = source_context.get('file_path', 'unknown')
        issue_line = source_context.get('issue_line', '')
        context_lines = source_context.get('context_lines', [])
        line_number = getattr(issue, 'line', 1)

        # Get more context around the issue
        context_code = '\n'.join(
            [f"{i+1}: {line}" for i, line in enumerate(context_lines)])

        prompt = f"""
You are an expert software engineer specializing in code fixes. Generate a precise fix plan for this SonarQube issue.

**Issue Details:**
- Rule: {issue.rule}
- Type: {issue.type}
- Severity: {getattr(issue, 'severity', 'UNKNOWN')}
- Message: {issue.message}
- File: {file_path}
- Line: {line_number}

**Code Context:**
```
{context_code}
```

**Problem Line:**
{issue_line}

Generate a JSON response with this structure:
{{
    "analysis": "Detailed analysis of what needs to be fixed and why",
    "solution": "Step-by-step solution description",
    "fixed_code": "The exact corrected code (if applicable)",
    "confidence": 0.85,
    "effort": "Low|Medium|High",
    "fix_type": "replace|delete|add|refactor",
    "side_effects": ["List of potential side effects or things to review"],
    "validation_steps": ["Steps to validate the fix works correctly"],
    "alternative_approaches": ["Other ways to fix this issue"]
}}

Requirements:
1. Provide working, syntactically correct code
2. Consider the broader context and impact
3. Suggest the safest, most maintainable solution
4. Be specific about what needs to change
5. Consider code style and best practices

Focus on practical, implementable solutions.
"""
        return prompt

    def _invoke_model(self, prompt: str) -> Optional[str]:
        """Invoke the Bedrock model with the given prompt."""
        if not self.bedrock:
            return None

        try:
            # Prepare the request body based on the model
            if "claude" in self.model_id.lower():
                body = {
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 2000,
                    "temperature": 0.1,
                    "messages": [
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ]
                }
            else:
                # Fallback for other models
                body = {
                    "inputText": prompt,
                    "textGenerationConfig": {
                        "maxTokenCount": 2000,
                        "temperature": 0.1
                    }
                }

            # Invoke the model
            response = self.bedrock.invoke_model(
                modelId=self.model_id,
                body=json.dumps(body),
                contentType="application/json",
                accept="application/json"
            )

            # Parse response
            response_body = json.loads(response['body'].read())

            if "claude" in self.model_id.lower():
                if 'content' in response_body and response_body['content']:
                    return response_body['content'][0]['text']
            else:
                if 'results' in response_body and response_body['results']:
                    return response_body['results'][0]['outputText']

        except Exception as e:
            print(f"❌ Error invoking Bedrock model: {e}")

        return None

    def _parse_analysis_response(self, response: str) -> Dict[str, Any]:
        """Parse the AI analysis response."""
        try:
            # Extract JSON from response
            json_start = response.find('{')
            json_end = response.rfind('}') + 1

            if json_start >= 0 and json_end > json_start:
                json_str = response[json_start:json_end]
                parsed = json.loads(json_str)

                # Validate required fields and set defaults
                return {
                    "root_cause": parsed.get("root_cause", "AI analysis pending"),
                    "impact_assessment": parsed.get("impact_assessment", "Impact analysis pending"),
                    "category": parsed.get("category", "general"),
                    "confidence": float(parsed.get("confidence", 0.7)),
                    "complexity": parsed.get("complexity", "Medium"),
                    "priority": parsed.get("priority", "Medium"),
                    "technical_details": parsed.get("technical_details", "Technical details pending")
                }
        except Exception as e:
            print(f"❌ Error parsing analysis response: {e}")

        # Fallback response
        return {
            "root_cause": "AI analysis failed - using fallback",
            "impact_assessment": "Unable to assess impact",
            "category": "general",
            "confidence": 0.5,
            "complexity": "Medium",
            "priority": "Medium",
            "technical_details": "AI analysis unavailable"
        }

    def _parse_fix_plan_response(self, response: str) -> Dict[str, Any]:
        """Parse the AI fix plan response."""
        try:
            # Extract JSON from response
            json_start = response.find('{')
            json_end = response.rfind('}') + 1

            if json_start >= 0 and json_end > json_start:
                json_str = response[json_start:json_end]
                parsed = json.loads(json_str)

                # Validate and return structured fix plan
                return {
                    "analysis": parsed.get("analysis", "AI analysis of the issue"),
                    "solution": parsed.get("solution", "AI-generated solution"),
                    "fixed_code": parsed.get("fixed_code", ""),
                    "confidence": float(parsed.get("confidence", 0.7)),
                    "effort": parsed.get("effort", "Medium"),
                    "fix_type": parsed.get("fix_type", "replace"),
                    "side_effects": parsed.get("side_effects", ["Review recommended"]),
                    "validation_steps": parsed.get("validation_steps", []),
                    "alternative_approaches": parsed.get("alternative_approaches", [])
                }
        except Exception as e:
            print(f"❌ Error parsing fix plan response: {e}")

        # Fallback response
        return {
            "analysis": "AI fix plan generation failed",
            "solution": "Manual review required",
            "fixed_code": "",
            "confidence": 0.4,
            "effort": "Medium",
            "fix_type": "replace",
            "side_effects": ["Manual review required"],
            "validation_steps": [],
            "alternative_approaches": []
        }

    def test_connection(self) -> bool:
        """Test connection to Bedrock."""
        if not self.bedrock:
            return False

        try:
            # Simple test prompt
            test_prompt = "Hello, can you respond with 'Connection successful'?"
            response = self._invoke_model(test_prompt)
            return response is not None
        except Exception:
            return False

    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the configured model."""
        return {
            "model_id": self.model_id,
            "region": self.region,
            "available": self.is_available,
            "provider": "AWS Bedrock"
        }
