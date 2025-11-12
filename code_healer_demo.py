#!/usr/bin/env python3
"""
Demonstration of Code Healer Agent functionality WITHOUT MCP tools.
Shows how to read, analyze, and fix Java files using standard Python operations.
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Optional

class CodeHealerDemo:
    """Demonstrates Code Healer functionality with standard file operations."""
    
    def __init__(self, repo_path: str):
        self.repo_path = Path(repo_path)
    
    def read_java_file(self, file_path: str) -> str:
        """Read entire Java file content."""
        full_path = self.repo_path / file_path
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
            return ""
    
    def write_java_file(self, file_path: str, content: str) -> bool:
        """Write content to Java file."""
        full_path = self.repo_path / file_path
        try:
            # Create backup first
            backup_path = f"{full_path}.backup"
            if full_path.exists():
                with open(full_path, 'r', encoding='utf-8') as f:
                    backup_content = f.read()
                with open(backup_path, 'w', encoding='utf-8') as f:
                    f.write(backup_content)
            
            # Write new content
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            print(f"✅ Successfully updated {file_path}")
            return True
        except Exception as e:
            print(f"❌ Error writing {file_path}: {e}")
            return False
    
    def get_line_context(self, file_path: str, target_line: int, context_lines: int = 5) -> Dict:
        """Get code context around a specific line."""
        content = self.read_java_file(file_path)
        if not content:
            return {}
        
        lines = content.split('\n')
        total_lines = len(lines)
        
        start_line = max(0, target_line - context_lines - 1)
        end_line = min(total_lines, target_line + context_lines)
        
        context_lines_list = lines[start_line:end_line]
        target_content = lines[target_line - 1] if target_line <= total_lines else ""
        
        return {
            'file_path': file_path,
            'target_line': target_line,
            'target_content': target_content,
            'context_content': '\n'.join(context_lines_list),
            'context_start_line': start_line + 1,
            'context_end_line': end_line,
            'total_lines': total_lines
        }
    
    def fix_connection_resource_leak(self, file_path: str, target_line: int) -> bool:
        """
        Fix Connection resource leak by converting to try-with-resources.
        This demonstrates the core fix logic without MCP tools.
        """
        print(f"\n🔧 Fixing Connection resource leak in {file_path}:{target_line}")
        
        # 1. Read the file
        content = self.read_java_file(file_path)
        if not content:
            return False
        
        lines = content.split('\n')
        
        # 2. Analyze the problematic code
        context = self.get_line_context(file_path, target_line, 10)
        print(f"📋 Target line: {context['target_content']}")
        
        # 3. Generate the fix using pattern matching and replacement
        fixed_content = self._apply_try_with_resources_fix(content, target_line)
        
        if fixed_content and fixed_content != content:
            # 4. Write the fixed content
            success = self.write_java_file(file_path, fixed_content)
            if success:
                print(f"✅ Applied try-with-resources fix to {file_path}")
                return True
        
        print(f"❌ Could not apply fix to {file_path}")
        return False
    
    def _apply_try_with_resources_fix(self, content: str, target_line: int) -> str:
        """
        Apply try-with-resources pattern to fix resource leaks.
        This is a simplified version - real implementation would use LLM.
        """
        lines = content.split('\n')
        
        # Find the method containing the target line
        method_start, method_end = self._find_method_boundaries(lines, target_line - 1)
        
        if method_start == -1 or method_end == -1:
            return content
        
        # Extract method content
        method_lines = lines[method_start:method_end + 1]
        
        # Apply fix pattern (simplified - real version would use LLM)
        fixed_method = self._convert_to_try_with_resources(method_lines)
        
        # Replace the method in the original content
        new_lines = lines[:method_start] + fixed_method + lines[method_end + 1:]
        
        return '\n'.join(new_lines)
    
    def _find_method_boundaries(self, lines: List[str], target_line_idx: int) -> tuple:
        """Find the start and end of the method containing the target line."""
        method_start = -1
        method_end = -1
        brace_count = 0
        
        # Find method start (look backwards for method signature)
        for i in range(target_line_idx, -1, -1):
            line = lines[i].strip()
            if re.match(r'.*\s+(public|private|protected).*\s+\w+\s*\([^)]*\)\s*\{?', line):
                method_start = i
                break
        
        if method_start == -1:
            return -1, -1
        
        # Find method end (count braces)
        for i in range(method_start, len(lines)):
            line = lines[i]
            brace_count += line.count('{') - line.count('}')
            if brace_count == 0 and i > method_start:
                method_end = i
                break
        
        return method_start, method_end
    
    def _convert_to_try_with_resources(self, method_lines: List[str]) -> List[str]:
        """
        Convert method to use try-with-resources pattern.
        This is a simplified pattern - real implementation would use LLM for complex cases.
        """
        # This is a simplified demonstration
        # Real implementation would:
        # 1. Parse Java AST or use LLM to understand code structure
        # 2. Identify resource declarations (Connection, Statement, etc.)
        # 3. Generate proper try-with-resources syntax
        # 4. Handle existing exception handling
        
        fixed_lines = []
        for line in method_lines:
            # Simple pattern replacement (demo only)
            if 'Connection conn = ' in line and 'DriverManager.getConnection' in line:
                # Convert to try-with-resources
                indent = len(line) - len(line.lstrip())
                resource_line = line.strip()
                fixed_lines.append(' ' * indent + f'try ({resource_line}) {{')
            elif 'conn.close()' in line:
                # Remove manual close - try-with-resources handles it
                continue
            else:
                fixed_lines.append(line)
        
        # Add closing brace for try-with-resources (simplified)
        if any('try (' in line for line in fixed_lines):
            # Find the last line with content and add closing brace
            for i in range(len(fixed_lines) - 1, -1, -1):
                if fixed_lines[i].strip():
                    indent = len(fixed_lines[i]) - len(fixed_lines[i].lstrip())
                    fixed_lines.insert(i + 1, ' ' * indent + '}')
                    break
        
        return fixed_lines

def demonstrate_code_healer():
    """Demonstrate Code Healer functionality."""
    print("🤖 Code Healer Agent Demo - WITHOUT MCP Tools")
    print("=" * 50)
    
    # Example: Fix the issue from Bug Hunter Agent output
    demo = CodeHealerDemo("D:/Intellij/SpringBootAppSonarAI")
    
    # This would come from Bug Hunter Agent's FixPlan
    fix_plan = {
        'issue_key': 'fbf3862c-84fb-41dc-bb84-51d0732b07fe',
        'file_path': 'src/main/java/com/example/springbootapp/controller/UserController.java',
        'line_number': 43,
        'issue_type': 'BLOCKER BUG: Use try-with-resources or close this "Connection" in a "finally" clause',
        'confidence': 1.00,
        'analysis': 'The code is not closing a JDBC Connection object after use, which can lead to resource leaks and other issues.',
        'solution': 'Use try-with-resources statement or close the Connection object in a finally block to ensure it is properly closed after use.'
    }
    
    print(f"📋 Processing Fix Plan:")
    print(f"   Issue: {fix_plan['issue_key']}")
    print(f"   File: {fix_plan['file_path']}:{fix_plan['line_number']}")
    print(f"   Type: {fix_plan['issue_type']}")
    print(f"   Confidence: {fix_plan['confidence']}")
    
    # 1. Read and analyze the problematic code
    context = demo.get_line_context(fix_plan['file_path'], fix_plan['line_number'])
    if context:
        print(f"\n📖 Code Context (lines {context['context_start_line']}-{context['context_end_line']}):")
        print("```java")
        print(context['context_content'])
        print("```")
        
        print(f"\n🎯 Target Line {fix_plan['line_number']}: {context['target_content']}")
    
    # 2. Apply the fix
    success = demo.fix_connection_resource_leak(fix_plan['file_path'], fix_plan['line_number'])
    
    if success:
        print(f"\n✅ SUCCESS: Resource leak fixed in {fix_plan['file_path']}")
        print("📝 Changes applied:")
        print("   - Converted manual Connection management to try-with-resources")
        print("   - Removed manual conn.close() call")
        print("   - Added automatic resource cleanup")
    else:
        print(f"\n❌ FAILED: Could not apply fix to {fix_plan['file_path']}")
    
    print(f"\n📊 Summary:")
    print(f"   - File operations: ✅ Standard Python file I/O")
    print(f"   - Code analysis: ✅ String parsing and regex")
    print(f"   - Fix application: ✅ Content replacement")
    print(f"   - Backup creation: ✅ Automatic backup before changes")
    print(f"   - No MCP tools needed: ✅ Works with existing capabilities")

if __name__ == "__main__":
    demonstrate_code_healer()