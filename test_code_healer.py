#!/usr/bin/env python3
"""
Test script for Code Healer Agent functionality.
Creates sample fix plans and tests the code healing process.
"""

import sys
import tempfile
import os
from pathlib import Path
from datetime import datetime

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from sonar_ai_agent.config import Config
from sonar_ai_agent.agents.code_healer_agent import CodeHealerAgent
from sonar_ai_agent.models import FixPlan


def create_sample_java_file() -> str:
    """Create a sample Java file with resource leak issues."""
    java_code = '''package com.example.springbootapp.controller;

import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.Statement;
import java.sql.ResultSet;
import java.sql.SQLException;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.bind.annotation.GetMapping;

@RestController
public class UserController {
    
    private static final String DB_URL = "jdbc:mysql://localhost:3306/testdb";
    private static final String USER = "user";
    private static final String PASS = "password";
    
    @GetMapping("/users")
    public String getUsers() {
        Connection conn = null;
        Statement stmt = null;
        ResultSet rs = null;
        
        try {
            // This line has a resource leak - connection not properly closed
            conn = DriverManager.getConnection(DB_URL, USER, PASS);
            stmt = conn.createStatement();
            rs = stmt.executeQuery("SELECT * FROM users");
            
            StringBuilder result = new StringBuilder();
            while (rs.next()) {
                result.append(rs.getString("name")).append(",");
            }
            
            return result.toString();
            
        } catch (SQLException e) {
            e.printStackTrace();
            return "Error: " + e.getMessage();
        }
        // Missing finally block to close resources - this is the issue!
    }
    
    @GetMapping("/user-count")
    public int getUserCount() {
        Connection conn = null;
        Statement stmt = null;
        ResultSet rs = null;
        
        try {
            conn = DriverManager.getConnection(DB_URL, USER, PASS);
            stmt = conn.createStatement();
            rs = stmt.executeQuery("SELECT COUNT(*) FROM users");
            
            if (rs.next()) {
                return rs.getInt(1);
            }
            
        } catch (SQLException e) {
            e.printStackTrace();
        } finally {
            // Partial resource cleanup - missing null checks
            try {
                rs.close();
                stmt.close();
                conn.close();
            } catch (SQLException e) {
                e.printStackTrace();
            }
        }
        
        return 0;
    }
}'''
    
    # Create temporary file
    temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.java', delete=False, encoding='utf-8')
    temp_file.write(java_code)
    temp_file.close()
    
    return temp_file.name


def create_sample_fix_plans(java_file_path: str) -> list:
    """Create sample fix plans for testing."""
    fix_plans = [
        FixPlan(
            issue_key="fbf3862c-84fb-41dc-bb84-51d0732b07fe",
            issue_description="BLOCKER BUG: Use try-with-resources or close this \"Connection\" in a \"finally\" clause.",
            file_path=java_file_path,
            line_number=25,
            problem_analysis="The code is not closing a JDBC Connection object after use, which can lead to resource leaks and connection pool exhaustion. The getUsers() method creates database connections but doesn't properly close them in a finally block or use try-with-resources.",
            proposed_solution="Convert the manual resource management to use try-with-resources statement, which automatically closes the Connection, Statement, and ResultSet objects when the try block exits, even if an exception occurs.",
            code_context="Method getUsers() in UserController class that queries database for user information",
            potential_side_effects=[
                "Code structure will change to use try-with-resources syntax",
                "Exception handling may need adjustment",
                "Variable scope will be limited to try block"
            ],
            confidence_score=0.95,
            estimated_effort="MEDIUM"
        ),
        FixPlan(
            issue_key="abc123-def456-ghi789-jkl012",
            issue_description="MAJOR BUG: Add null checks before closing resources in finally block.",
            file_path=java_file_path,
            line_number=58,
            problem_analysis="The getUserCount() method attempts to close database resources in a finally block but doesn't check for null values first. This can cause NullPointerException if resource initialization failed.",
            proposed_solution="Add null checks before attempting to close each resource (ResultSet, Statement, Connection) in the finally block to prevent NullPointerException.",
            code_context="Method getUserCount() in UserController class finally block",
            potential_side_effects=[
                "Additional null checks will be added",
                "Code will be more defensive against initialization failures"
            ],
            confidence_score=0.88,
            estimated_effort="LOW"
        )
    ]
    
    return fix_plans


def main():
    """Test the Code Healer Agent."""
    print("🔧 Code Healer Agent Test")
    print("=" * 50)
    
    try:
        # Load configuration
        config = Config()
        print(f"✅ Configuration loaded")
        print(f"   - Ollama Model: {config.ollama_model}")
        print(f"   - Log File: {config.log_file}")
        
        # Create sample Java file
        java_file_path = create_sample_java_file()
        print(f"✅ Created sample Java file: {java_file_path}")
        
        # Create sample fix plans
        fix_plans = create_sample_fix_plans(java_file_path)
        print(f"✅ Created {len(fix_plans)} sample fix plans")
        
        # Initialize Code Healer Agent
        code_healer = CodeHealerAgent(config)
        print(f"✅ Code Healer Agent initialized")
        
        # Test health check
        if code_healer.health_check():
            print(f"✅ Code Healer health check passed")
        else:
            print(f"❌ Code Healer health check failed")
            return 1
        
        print(f"\n🔄 Processing fix plans...")
        print("-" * 30)
        
        # Process the fix plans
        results = code_healer.process(fix_plans)
        
        # Display results
        print(f"\n📊 Code Healer Results:")
        print("-" * 30)
        print(f"Session ID: {results['session_id']}")
        print(f"Total Fix Plans: {results['total_fix_plans']}")
        print(f"Fixes Applied: {results['fixes_applied']}")
        print(f"Fixes Validated: {results['fixes_validated']}")
        print(f"Branches Created: {results['branches_created']}")
        print(f"Merge Requests: {results['merge_requests_created']}")
        print(f"Success Rate: {results['success_rate']:.2%}")
        
        # Show applied fixes
        applied_fixes = results.get('applied_fixes', [])
        if applied_fixes:
            print(f"\n🔧 Applied Fixes:")
            print("-" * 30)
            for i, fix in enumerate(applied_fixes, 1):
                print(f"\n{i}. Issue: {fix.fix_plan.issue_key}")
                print(f"   File: {fix.fix_plan.file_path}:{fix.fix_plan.line_number}")
                print(f"   Validation: {'✅ Passed' if fix.is_valid else '❌ Failed'}")
                print(f"   Branch: {fix.branch_name}")
                
                if fix.validation_errors:
                    print(f"   Errors: {', '.join(fix.validation_errors[:2])}")
                
                # Show diff preview
                diff_lines = fix.diff.split('\n')
                relevant_diff = [line for line in diff_lines if line.startswith(('+', '-')) and not line.startswith(('+++', '---'))]
                if relevant_diff:
                    print(f"   Changes: {len(relevant_diff)} lines modified")
                    # Show first few changes
                    for line in relevant_diff[:3]:
                        print(f"     {line}")
                    if len(relevant_diff) > 3:
                        print(f"     ... and {len(relevant_diff) - 3} more changes")
        
        # Show created branches
        created_branches = results.get('created_branches', [])
        if created_branches:
            print(f"\n🌿 Created Git Branches:")
            for branch in created_branches:
                print(f"   - {branch}")
        
        # Show merge requests
        merge_requests = results.get('merge_requests', [])
        if merge_requests:
            print(f"\n🔀 Created Merge Requests:")
            for mr in merge_requests:
                print(f"   - {mr}")
        
        # Show errors
        errors = results.get('errors', [])
        if errors:
            print(f"\n❌ Errors Encountered:")
            for error in errors:
                print(f"   - {error}")
        
        print(f"\n📁 Check the modified file:")
        print(f"   {java_file_path}")
        
        print(f"\n📝 Detailed logs available at:")
        print(f"   {config.log_file}")
        
        # Show the modified file content
        print(f"\n📄 Modified File Content:")
        print("-" * 50)
        try:
            with open(java_file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')
                for i, line in enumerate(lines[:20], 1):  # Show first 20 lines
                    print(f"{i:3d}: {line}")
                if len(lines) > 20:
                    print(f"... and {len(lines) - 20} more lines")
        except Exception as e:
            print(f"Error reading modified file: {e}")
        
        print(f"\n✅ Code Healer test completed successfully!")
        
        return 0
        
    except KeyboardInterrupt:
        print(f"\n⏹️ Test interrupted by user")
        return 1
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    finally:
        # Cleanup temporary file
        if 'java_file_path' in locals() and os.path.exists(java_file_path):
            try:
                os.unlink(java_file_path)
                print(f"🧹 Cleaned up temporary file: {java_file_path}")
            except Exception as e:
                print(f"⚠️ Could not cleanup temporary file: {e}")


if __name__ == "__main__":
    exit(main())