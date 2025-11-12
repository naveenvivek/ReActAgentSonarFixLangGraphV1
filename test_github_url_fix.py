#!/usr/bin/env python3
"""
Test script to verify GitHub URL generation fix.
"""

import sys
import os
from unittest.mock import patch, MagicMock

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sonar_ai_agent.config import Config
from sonar_ai_agent.agents.code_healer_agent import CodeHealerAgent
from sonar_ai_agent.models import FixPlan, CodeFix


def test_github_url_generation():
    """Test that proper GitHub URLs are generated instead of dummy URLs."""
    print("Testing GitHub URL Generation Fix...")
    print("=" * 40)
    
    # Mock the required environment variables
    with patch.dict(os.environ, {
        'SONAR_TOKEN': 'test_token',
        'TARGET_REPO_URL': 'https://github.com/naveenvivek/SpringBootAppSonarAI',
        'TARGET_REPO_PATH': '/tmp/test_repo',
        'TARGET_REPO_BRANCH': 'main',
        'GITHUB_TOKEN': 'test_github_token'
    }):
        config = Config()
        
        # Create a mock Code Healer Agent
        agent = CodeHealerAgent(config)
        
        # Create a mock fix for testing
        mock_fix_plan = MagicMock()
        mock_fix_plan.issue_key = "java:S2095"
        mock_fix_plan.file_path = "src/main/java/UserController.java"
        mock_fix_plan.line_number = 42
        mock_fix_plan.confidence_score = 0.85
        mock_fix_plan.problem_analysis = "Resource leak detected"
        mock_fix_plan.proposed_solution = "Use try-with-resources"
        mock_fix_plan.potential_side_effects = []
        
        mock_code_fix = MagicMock()
        mock_code_fix.fix_plan = mock_fix_plan
        mock_code_fix.validation_status = True
        mock_code_fix.diff = "- old code\n+ new code"
        
        # Test single fix URL generation
        print("1. Testing single fix URL generation:")
        branch_name = "fix/sonar-java-S2095-UserController-resource-leak"
        
        try:
            url = agent._create_merge_request([mock_code_fix], branch_name)
            print(f"   Generated URL: {url}")
            
            # Verify it's a proper GitHub URL
            expected_base = "https://github.com/naveenvivek/SpringBootAppSonarAI/compare/main..."
            if url and expected_base in url:
                print("   ✅ Proper GitHub URL generated!")
            else:
                print(f"   ❌ Expected GitHub URL, got: {url}")
        
        except Exception as e:
            print(f"   ❌ Error generating URL: {e}")
        
        # Test batch fix URL generation
        print("\n2. Testing batch fix URL generation:")
        batch_branch_name = "fix/sonar-batch-20251112_223000-resource-leaks"
        
        try:
            batch_url = agent._create_merge_request([mock_code_fix, mock_code_fix], batch_branch_name)
            print(f"   Generated URL: {batch_url}")
            
            # Verify it's a proper GitHub URL
            if batch_url and expected_base in batch_url:
                print("   ✅ Proper GitHub batch URL generated!")
            else:
                print(f"   ❌ Expected GitHub URL, got: {batch_url}")
        
        except Exception as e:
            print(f"   ❌ Error generating batch URL: {e}")
        
        print("\n3. Testing with non-GitHub repository:")
        # Test with non-GitHub URL
        config.target_repo_url = "https://gitlab.com/user/repo"
        try:
            gitlab_url = agent._create_merge_request([mock_code_fix], branch_name)
            print(f"   Generated URL: {gitlab_url}")
            
            if gitlab_url and "Pull request ready for branch:" in gitlab_url:
                print("   ✅ Proper fallback message generated!")
            else:
                print(f"   ❌ Expected fallback message, got: {gitlab_url}")
        
        except Exception as e:
            print(f"   ❌ Error generating fallback URL: {e}")


if __name__ == "__main__":
    test_github_url_generation()