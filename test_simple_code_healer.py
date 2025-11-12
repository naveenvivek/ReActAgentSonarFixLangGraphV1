#!/usr/bin/env python3
"""
Simple test script for Code Healer Agent functionality.
Creates a basic Java file without Spring Boot dependencies for testing.
"""

import sys
import tempfile
import os
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from sonar_ai_agent.config import Config
from sonar_ai_agent.agents.code_healer_agent import CodeHealerAgent
from sonar_ai_agent.models import FixPlan


def create_simple_java_file() -> str:
    """Create a simple Java file with resource leak issues (no Spring Boot)."""
    java_code = '''import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.Statement;
import java.sql.ResultSet;
import java.sql.SQLException;

public class DatabaseHelper {
    
    private static final String DB_URL = "jdbc:mysql://localhost:3306/testdb";
    private static final String USER = "user";
    private static final String PASS = "password";
    
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
    
    # Create temporary file with proper Java class name
    temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='DatabaseHelper.java', delete=False, encoding='utf-8')
    temp_file.write(java_code)
    temp_file.close()
    
    return temp_file.name


def create_simple_fix_plans(java_file_path: str) -> list:
    """Create simple fix plans for testing."""
    fix_plans = [
        FixPlan(
            issue_key="resource-leak-001",
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
    ]
    
    return fix_plans


def main():
    """Test the Code Healer Agent with simple Java code."""
    print("🔧 Simple Code Healer Agent Test")
    print("=" * 50)
    
    try:
        # Load configuration
        config = Config()
        print(f"✅ Configuration loaded")
        
        # Disable compilation validation for this test
        java_file_path = create_simple_java_file()
        print(f"✅ Created simple Java file: {java_file_path}")
        
        # Create fix plans
        fix_plans = create_simple_fix_plans(java_file_path)
        print(f"✅ Created {len(fix_plans)} fix plans")
        
        # Initialize Code Healer Agent
        code_healer = CodeHealerAgent(config)
        # Disable compilation validation for this test
        code_healer.validate_compilation = False
        print(f"✅ Code Healer Agent initialized (validation disabled)")
        
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
                
                if fix.validation_errors:
                    print(f"   Errors: {', '.join(fix.validation_errors[:2])}")
                
                # Show diff preview
                diff_lines = fix.diff.split('\n')
                relevant_diff = [line for line in diff_lines if line.startswith(('+', '-')) and not line.startswith(('+++', '---'))]
                if relevant_diff:
                    print(f"   Changes: {len(relevant_diff)} lines modified")
                    print(f"   Sample changes:")
                    for line in relevant_diff[:5]:
                        print(f"     {line}")
        
        # Show the modified file content
        print(f"\n📄 Modified File Content:")
        print("-" * 50)
        try:
            with open(java_file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                print(content)
        except Exception as e:
            print(f"Error reading modified file: {e}")
        
        print(f"\n✅ Simple Code Healer test completed!")
        
        return 0
        
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