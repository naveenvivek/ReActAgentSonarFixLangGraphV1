#!/usr/bin/env python3
"""
Demonstration of how to edit Java files WITHOUT MCP tools.
Shows the exact mechanism for reading, modifying, and writing Java files.
"""

import os
from pathlib import Path

def demonstrate_java_file_editing():
    """Show exactly how to edit Java files with standard Python operations."""
    
    print("🔧 Java File Editing Demo - Standard Python Operations")
    print("=" * 60)
    
    # Create a sample Java file to demonstrate editing
    sample_java_content = '''package com.example.springbootapp.controller;

import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.Statement;
import java.sql.SQLException;

public class UserController {
    
    public void createUser(String name) {
        Connection conn = null;
        Statement stmt = null;
        
        try {
            // PROBLEMATIC CODE - Resource leak (line 15)
            conn = DriverManager.getConnection("jdbc:mysql://localhost/db");
            stmt = conn.createStatement();
            
            String sql = "INSERT INTO users (name) VALUES ('" + name + "')";
            stmt.executeUpdate(sql);
            
            System.out.println("User created successfully");
            
        } catch (SQLException e) {
            e.printStackTrace();
        }
        // MISSING: No proper resource cleanup - this causes resource leaks!
    }
}'''
    
    # Write the sample file
    sample_file = "UserController.java"
    with open(sample_file, 'w', encoding='utf-8') as f:
        f.write(sample_java_content)
    
    print(f"📝 Created sample Java file: {sample_file}")
    print("\n📖 Original Code (with resource leak):")
    print("```java")
    print(sample_java_content)
    print("```")
    
    # Now demonstrate how to fix it
    print(f"\n🔧 STEP 1: Read the Java file")
    
    # Read the file content
    with open(sample_file, 'r', encoding='utf-8') as f:
        original_content = f.read()
    
    print(f"✅ File read successfully ({len(original_content)} characters)")
    
    print(f"\n🔧 STEP 2: Modify the content in memory")
    
    # Apply the fix - convert to try-with-resources
    fixed_content = apply_try_with_resources_fix(original_content)
    
    print(f"✅ Content modified in memory")
    
    print(f"\n🔧 STEP 3: Write the fixed content back to file")
    
    # Create backup first
    backup_file = f"{sample_file}.backup"
    with open(backup_file, 'w', encoding='utf-8') as f:
        f.write(original_content)
    print(f"✅ Backup created: {backup_file}")
    
    # Write the fixed content
    with open(sample_file, 'w', encoding='utf-8') as f:
        f.write(fixed_content)
    
    print(f"✅ Fixed content written to: {sample_file}")
    
    print(f"\n📖 Fixed Code (resource leak resolved):")
    print("```java")
    print(fixed_content)
    print("```")
    
    print(f"\n📊 Summary of File Operations:")
    print(f"   1. READ: open(file, 'r') → content string")
    print(f"   2. MODIFY: string manipulation → fixed_content")
    print(f"   3. BACKUP: open(backup, 'w') → save original")
    print(f"   4. WRITE: open(file, 'w') → save fixed content")
    
    # Cleanup
    os.remove(sample_file)
    os.remove(backup_file)
    print(f"\n🧹 Demo files cleaned up")

def apply_try_with_resources_fix(java_content: str) -> str:
    """
    Apply try-with-resources fix to Java code.
    This shows the actual string manipulation that fixes the resource leak.
    """
    lines = java_content.split('\n')
    fixed_lines = []
    
    i = 0
    while i < len(lines):
        line = lines[i]
        
        # Look for the problematic pattern
        if 'conn = DriverManager.getConnection' in line:
            # Found the resource leak - convert to try-with-resources
            
            # Get the indentation
            indent = len(line) - len(line.lstrip())
            base_indent = ' ' * indent
            
            # Find the statement creation line
            stmt_line = None
            for j in range(i + 1, min(i + 5, len(lines))):
                if 'stmt = conn.createStatement' in lines[j]:
                    stmt_line = j
                    break
            
            # Create try-with-resources block
            conn_declaration = line.strip().replace('conn = ', 'Connection conn = ')
            
            if stmt_line:
                stmt_declaration = lines[stmt_line].strip().replace('stmt = ', 'Statement stmt = ')
                
                # Add try-with-resources with both Connection and Statement
                fixed_lines.append(f'{base_indent}try ({conn_declaration};')
                fixed_lines.append(f'{base_indent}     {stmt_declaration}) {{')
                
                # Skip the original stmt line
                i = stmt_line + 1
            else:
                # Just Connection
                fixed_lines.append(f'{base_indent}try ({conn_declaration}) {{')
                i += 1
            
            # Add increased indentation for the try block content
            try_indent = base_indent + '    '
            
            # Process the rest of the method until we find the catch block
            while i < len(lines):
                current_line = lines[i]
                
                if '} catch (' in current_line:
                    # End the try-with-resources block and add catch
                    fixed_lines.append(f'{base_indent}}} catch (SQLException e) {{')
                    i += 1
                    break
                elif current_line.strip().startswith('} catch'):
                    # End the try-with-resources block and add catch
                    fixed_lines.append(f'{base_indent}}} catch (SQLException e) {{')
                    i += 1
                    break
                else:
                    # Add line with proper indentation inside try block
                    if current_line.strip():
                        fixed_lines.append(f'{try_indent}{current_line.lstrip()}')
                    else:
                        fixed_lines.append(current_line)
                    i += 1
        else:
            # Regular line - keep as is
            fixed_lines.append(line)
            i += 1
    
    return '\n'.join(fixed_lines)

def demonstrate_string_replacement_method():
    """Show alternative method using string replacement."""
    
    print(f"\n🔧 Alternative Method: String Replacement")
    print("=" * 50)
    
    original_code = '''        try {
            conn = DriverManager.getConnection("jdbc:mysql://localhost/db");
            stmt = conn.createStatement();
            
            String sql = "INSERT INTO users (name) VALUES ('" + name + "')";
            stmt.executeUpdate(sql);'''
    
    print("📖 Original problematic code:")
    print(original_code)
    
    # Method 1: Direct string replacement
    fixed_code = original_code.replace(
        'conn = DriverManager.getConnection("jdbc:mysql://localhost/db");\n            stmt = conn.createStatement();',
        'try (Connection conn = DriverManager.getConnection("jdbc:mysql://localhost/db");\n                 Statement stmt = conn.createStatement()) {'
    )
    
    print(f"\n📖 Fixed code:")
    print(fixed_code)
    
    print(f"\n✅ String replacement method works for simple cases!")

if __name__ == "__main__":
    demonstrate_java_file_editing()
    demonstrate_string_replacement_method()