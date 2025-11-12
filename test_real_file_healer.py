#!/usr/bin/env python3
"""
Test Code Healer Agent with actual repository files to demonstrate Git commit functionality.
"""

import sys
import os
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from sonar_ai_agent.config import Config
from sonar_ai_agent.agents.code_healer_agent import CodeHealerAgent
from sonar_ai_agent.models import FixPlan


def main():
    """Test Code Healer Agent with actual repository file."""
    print("🔧 Code Healer Agent - Real File Test")
    print("=" * 50)
    
    try:
        # Load configuration
        config = Config()
        print(f"✅ Configuration loaded")
        
        # Use actual file in repository
        java_file_path = "test_files/DatabaseHelper.java"
        
        if not os.path.exists(java_file_path):
            print(f"❌ Test file not found: {java_file_path}")
            return 1
        
        print(f"✅ Using actual repository file: {java_file_path}")
        
        # Create fix plan for the actual file
        fix_plan = FixPlan(
            issue_key="real-file-test-001",
            issue_description="BLOCKER BUG: Use try-with-resources or close this \"Connection\" in a \"finally\" clause.",
            file_path=java_file_path,
            line_number=18,
            problem_analysis="The getUsers() method creates database connections but doesn't properly close them in a finally block or use try-with-resources. This can lead to resource leaks and connection pool exhaustion.",
            proposed_solution="Convert the manual resource management to use try-with-resources statement, which automatically closes the Connection, Statement, and ResultSet objects when the try block exits.",
            code_context="Method getUsers() in DatabaseHelper class that queries database for user information",
            potential_side_effects=[
                "Code structure will change to use try-with-resources syntax",
                "Variable scope will be limited to try block"
            ],
            confidence_score=0.95,
            estimated_effort="MEDIUM"
        )
        
        print(f"✅ Created fix plan for actual file")
        
        # Initialize Code Healer Agent
        code_healer = CodeHealerAgent(config)
        # Disable compilation validation for this test (no Java compiler setup)
        code_healer.validate_compilation = False
        print(f"✅ Code Healer Agent initialized")
        
        # Show original file content
        print(f"\n📄 Original File Content:")
        print("-" * 30)
        with open(java_file_path, 'r', encoding='utf-8') as f:
            original_content = f.read()
            lines = original_content.split('\n')
            for i, line in enumerate(lines[:15], 1):  # Show first 15 lines
                marker = " -> " if i == 18 else "    "
                print(f"{i:3d}{marker}{line}")
            print(f"... and {len(lines) - 15} more lines")
        
        print(f"\n🔄 Processing fix plan...")
        print("-" * 30)
        
        # Process the fix plan
        results = code_healer.process([fix_plan])
        
        # Display results
        print(f"\n📊 Code Healer Results:")
        print("-" * 30)
        print(f"Session ID: {results['session_id']}")
        print(f"Total Fix Plans: {results['total_fix_plans']}")
        print(f"Fixes Applied: {results['fixes_applied']}")
        print(f"Fixes Validated: {results['fixes_validated']}")
        print(f"Branches Created: {results['branches_created']}")
        print(f"Success Rate: {results['success_rate']:.2%}")
        
        # Show Git operations
        created_branches = results.get('created_branches', [])
        if created_branches:
            print(f"\n🌿 Git Branches Created:")
            for branch in created_branches:
                print(f"   ✅ {branch}")
        
        merge_requests = results.get('merge_requests', [])
        if merge_requests:
            print(f"\n🔀 Merge Requests Ready:")
            for mr in merge_requests:
                print(f"   📝 {mr}")
        
        # Show errors if any
        errors = results.get('errors', [])
        if errors:
            print(f"\n❌ Errors:")
            for error in errors:
                print(f"   - {error}")
        
        # Show modified file content
        print(f"\n📄 Modified File Content:")
        print("-" * 30)
        with open(java_file_path, 'r', encoding='utf-8') as f:
            modified_content = f.read()
            lines = modified_content.split('\n')
            for i, line in enumerate(lines[:20], 1):  # Show first 20 lines
                print(f"{i:3d}:   {line}")
            if len(lines) > 20:
                print(f"... and {len(lines) - 20} more lines")
        
        # Check Git status
        print(f"\n🔍 Git Status Check:")
        print("-" * 30)
        
        try:
            import subprocess
            result = subprocess.run(['git', 'status', '--porcelain'], 
                                  capture_output=True, text=True, cwd='.')
            if result.returncode == 0:
                if result.stdout.strip():
                    print("📝 Git changes detected:")
                    for line in result.stdout.strip().split('\n'):
                        print(f"   {line}")
                else:
                    print("✅ No uncommitted changes (file was committed)")
            else:
                print(f"❌ Git status check failed: {result.stderr}")
        except Exception as e:
            print(f"⚠️ Could not check Git status: {e}")
        
        # Check current branch
        try:
            result = subprocess.run(['git', 'branch', '--show-current'], 
                                  capture_output=True, text=True, cwd='.')
            if result.returncode == 0:
                current_branch = result.stdout.strip()
                print(f"🌿 Current Git branch: {current_branch}")
            else:
                print(f"❌ Could not get current branch: {result.stderr}")
        except Exception as e:
            print(f"⚠️ Could not check current branch: {e}")
        
        print(f"\n✅ Real file Code Healer test completed!")
        print(f"📁 Modified file: {java_file_path}")
        print(f"📝 Check Git history for commits")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())