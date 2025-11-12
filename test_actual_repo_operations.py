#!/usr/bin/env python3
"""
Test script to verify Git operations with the actual repository.
"""

import sys
import os
import subprocess
from pathlib import Path

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sonar_ai_agent.config import Config
from sonar_ai_agent.integrations.git_client import GitClient


def test_actual_repo_operations():
    """Test Git operations with the actual SpringBootAppSonarAI repository."""
    print("Testing Git Operations with Actual Repository...")
    print("=" * 50)
    
    # Use actual repository path
    actual_repo_path = r"D:\Intellij\SpringBootAppSonarAI"
    
    if not os.path.exists(actual_repo_path):
        print(f"❌ Repository not found at: {actual_repo_path}")
        return
    
    print(f"✅ Repository found at: {actual_repo_path}")
    
    # Create config with actual repository
    config = Config()
    config.target_repo_path = actual_repo_path
    config.target_repo_url = "https://github.com/naveenvivek/SpringBootAppSonarAI"
    config.target_repo_branch = "master"  # or "main"
    
    git_client = GitClient(config)
    
    print("\n1. Testing repository info:")
    repo_info = git_client.get_repository_info()
    for key, value in repo_info.items():
        print(f"   {key}: {value}")
    
    print("\n2. Testing current branch:")
    current_branch = git_client.get_current_branch()
    print(f"   Current branch: {current_branch}")
    
    print("\n3. Testing branch creation (dry run):")
    test_branch_name = "test/git-operations-verification"
    
    try:
        # Check if test branch already exists and clean it up
        result = subprocess.run(['git', 'branch', '--list', test_branch_name], 
                              cwd=actual_repo_path, capture_output=True, text=True)
        if test_branch_name in result.stdout:
            print(f"   Cleaning up existing test branch: {test_branch_name}")
            subprocess.run(['git', 'checkout', config.target_repo_branch], 
                         cwd=actual_repo_path, capture_output=True, text=True)
            subprocess.run(['git', 'branch', '-D', test_branch_name], 
                         cwd=actual_repo_path, capture_output=True, text=True)
        
        # Test branch creation
        print(f"   Creating test branch: {test_branch_name}")
        branch_created = git_client.create_branch(test_branch_name)
        print(f"   Branch creation result: {branch_created}")
        
        if branch_created:
            # Verify branch exists
            result = subprocess.run(['git', 'branch', '--list', test_branch_name], 
                                  cwd=actual_repo_path, capture_output=True, text=True)
            branch_exists = test_branch_name in result.stdout
            print(f"   Branch exists locally: {branch_exists}")
            
            # Test creating a dummy file and committing
            print(f"\n4. Testing commit operations:")
            test_file_path = os.path.join(actual_repo_path, "test_git_operations.txt")
            
            # Create a test file
            with open(test_file_path, 'w') as f:
                f.write("This is a test file for Git operations verification.\n")
                f.write(f"Created at: {datetime.now().isoformat()}\n")
            
            print(f"   Created test file: test_git_operations.txt")
            
            # Test commit
            commit_result = git_client.commit_changes(
                ["test_git_operations.txt"], 
                "test: verify Git operations functionality"
            )
            print(f"   Commit result: {commit_result}")
            
            if commit_result:
                print(f"\n5. Testing push operations (WARNING: This will push to remote!):")
                
                # Ask user for confirmation before pushing
                response = input("   Do you want to test pushing to remote? (y/N): ").strip().lower()
                
                if response == 'y':
                    push_result = git_client.push_branch(test_branch_name)
                    print(f"   Push result: {push_result}")
                    
                    if push_result:
                        print(f"   ✅ Branch successfully pushed to remote!")
                        print(f"   🔗 GitHub URL: https://github.com/naveenvivek/SpringBootAppSonarAI/tree/{test_branch_name}")
                        print(f"   🔗 Create PR: https://github.com/naveenvivek/SpringBootAppSonarAI/compare/master...{test_branch_name}?expand=1")
                    else:
                        print(f"   ❌ Failed to push branch to remote")
                else:
                    print("   Skipping push test (user declined)")
            
            # Clean up
            print(f"\n6. Cleaning up test artifacts:")
            
            # Switch back to main branch
            subprocess.run(['git', 'checkout', config.target_repo_branch], 
                         cwd=actual_repo_path, capture_output=True, text=True)
            print(f"   Switched back to {config.target_repo_branch}")
            
            # Delete test file if it exists
            if os.path.exists(test_file_path):
                os.remove(test_file_path)
                print(f"   Removed test file")
            
            # Delete local test branch
            subprocess.run(['git', 'branch', '-D', test_branch_name], 
                         cwd=actual_repo_path, capture_output=True, text=True)
            print(f"   Deleted local test branch")
            
            # If branch was pushed, inform user about remote cleanup
            if 'push_result' in locals() and push_result:
                print(f"   ⚠️  Remote branch still exists: {test_branch_name}")
                print(f"   You may want to delete it manually from GitHub")
    
    except Exception as e:
        print(f"   ❌ Error during testing: {e}")
    
    print(f"\n✅ Git operations test completed!")


if __name__ == "__main__":
    from datetime import datetime
    test_actual_repo_operations()