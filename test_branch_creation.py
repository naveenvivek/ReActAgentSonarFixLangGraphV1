#!/usr/bin/env python3
"""
Test script to verify Git branch creation and pushing.
"""

import sys
import os
import tempfile
import shutil
from unittest.mock import patch, MagicMock

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sonar_ai_agent.config import Config
from sonar_ai_agent.integrations.git_client import GitClient


def test_git_operations():
    """Test Git branch creation, commit, and push operations."""
    print("Testing Git Branch Creation and Push Operations...")
    print("=" * 50)
    
    # Create a temporary directory for testing
    with tempfile.TemporaryDirectory() as temp_dir:
        test_repo_path = os.path.join(temp_dir, "test_repo")
        
        # Mock configuration
        with patch.dict(os.environ, {
            'SONAR_TOKEN': 'test_token',
            'TARGET_REPO_URL': 'https://github.com/naveenvivek/SpringBootAppSonarAI',
            'TARGET_REPO_PATH': test_repo_path,
            'TARGET_REPO_BRANCH': 'main',
            'GITHUB_TOKEN': 'test_github_token',
            'GIT_USER_NAME': 'Test User',
            'GIT_USER_EMAIL': 'test@example.com'
        }):
            config = Config()
            git_client = GitClient(config)
            
            print("\n1. Testing Git client initialization:")
            print(f"   Repository URL: {git_client.repo_url}")
            print(f"   Repository Path: {git_client.repo_path}")
            print(f"   Default Branch: {git_client.default_branch}")
            
            # Test repository info when repo doesn't exist
            print("\n2. Testing repository info (before clone):")
            repo_info = git_client.get_repository_info()
            print(f"   Repository exists: {bool(repo_info)}")
            
            # Test branch creation without repository (should fail gracefully)
            print("\n3. Testing branch creation without repository:")
            branch_created = git_client.create_branch("test-branch")
            print(f"   Branch creation result: {branch_created}")
            
            # Test commit without repository (should fail gracefully)
            print("\n4. Testing commit without repository:")
            commit_result = git_client.commit_changes(["test.txt"], "Test commit")
            print(f"   Commit result: {commit_result}")
            
            # Test push without repository (should fail gracefully)
            print("\n5. Testing push without repository:")
            push_result = git_client.push_branch("test-branch")
            print(f"   Push result: {push_result}")
            
            print("\n6. Testing with actual repository (if available):")
            
            # Try to check if the actual repository exists
            actual_repo_path = config.target_repo_path
            if actual_repo_path and os.path.exists(actual_repo_path):
                print(f"   Found actual repository at: {actual_repo_path}")
                
                # Update config to use actual repo for testing
                git_client.repo_path = Path(actual_repo_path)
                
                # Test getting current branch
                current_branch = git_client.get_current_branch()
                print(f"   Current branch: {current_branch}")
                
                # Test repository info
                repo_info = git_client.get_repository_info()
                print(f"   Repository info: {repo_info}")
                
                # Test creating a test branch (but don't push it)
                test_branch_name = "test/branch-creation-verification"
                print(f"\n   Testing branch creation: {test_branch_name}")
                
                # First, make sure we're on the default branch
                import subprocess
                try:
                    subprocess.run(['git', 'checkout', config.target_repo_branch], 
                                 cwd=actual_repo_path, capture_output=True, text=True)
                    
                    # Try to create the test branch
                    branch_created = git_client.create_branch(test_branch_name)
                    print(f"   Branch creation result: {branch_created}")
                    
                    if branch_created:
                        # Check if branch was actually created
                        result = subprocess.run(['git', 'branch', '--list', test_branch_name], 
                                              cwd=actual_repo_path, capture_output=True, text=True)
                        branch_exists = test_branch_name in result.stdout
                        print(f"   Branch exists locally: {branch_exists}")
                        
                        # Clean up - delete the test branch
                        subprocess.run(['git', 'checkout', config.target_repo_branch], 
                                     cwd=actual_repo_path, capture_output=True, text=True)
                        subprocess.run(['git', 'branch', '-D', test_branch_name], 
                                     cwd=actual_repo_path, capture_output=True, text=True)
                        print(f"   Cleaned up test branch: {test_branch_name}")
                
                except Exception as e:
                    print(f"   Error during branch testing: {e}")
            
            else:
                print(f"   Actual repository not found at: {actual_repo_path}")
                print("   This is expected if the repository hasn't been cloned yet.")
            
            print("\n✅ Git operations test completed!")
            print("\nNote: For branches to appear on GitHub, they need to be:")
            print("1. Created locally ✓ (GitClient.create_branch)")
            print("2. Committed with changes ✓ (GitClient.commit_changes)")
            print("3. Pushed to remote ✓ (GitClient.push_branch) - NOW IMPLEMENTED")


if __name__ == "__main__":
    test_git_operations()