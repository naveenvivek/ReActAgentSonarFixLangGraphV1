# Code Healer Agent Specification

## Overview

The Code Healer Agent is the second agent in the SonarQube AI Agent system that receives fix plans from the Bug Hunter Agent and applies actual code fixes to the Java codebase. It reads the structured fix suggestions, generates concrete code changes, validates the fixes, and creates Git branches with merge requests.

## Input Format

The Code Healer Agent will process fix plans in this format:

```
Issue: fbf3862c-84fb-41dc-bb84-51d0732b07fe
File: src/main/java/com/example/springbootapp/controller/UserController.java:43
Type: BLOCKER BUG: Use try-with-resources or close this "Connection" in a "finally" clause.
Confidence: 1.00
Effort: MEDIUM
Analysis: The code is not closing a JDBC Connection object after use, which can lead to resource leaks and other issues.
Solution: Use try-with-resources statement or close the Connection object in a finally block to ensure it is properly closed after use.
Side Effects: Implementing this fix will require modifying the existing code to either use try-with-resources or add a finally block to close the Connection object.
```

## Core Functionality

### 1. Fix Plan Processing
- **Input**: FixPlan objects from Bug Hunter Agent
- **Parse**: Extract issue details, file path, line number, and solution strategy
- **Validate**: Ensure fix plan has sufficient information for implementation

### 2. Code Analysis and Context Reading
- **File Reading**: Read the target Java file and surrounding code context
- **Issue Location**: Identify the exact problematic code at the specified line
- **Code Understanding**: Analyze the current code structure and patterns
- **Dependencies**: Identify imports, variables, and method signatures that may be affected

### 3. Fix Generation with LLM
- **Prompt Engineering**: Create specialized prompts for Java code fixing
- **LLM Integration**: Use Ollama to generate actual code fixes
- **Multiple Strategies**: Support different fix approaches (try-with-resources, finally blocks, etc.)
- **Code Validation**: Ensure generated code follows Java syntax and best practices

### 4. Code Application and Validation
- **File Modification**: Apply the generated fixes to the actual Java files
- **Syntax Validation**: Verify the modified code compiles correctly
- **Backup Creation**: Create backups before applying changes
- **Rollback Capability**: Ability to revert changes if validation fails

### 5. Git Integration
- **Branch Creation**: Create feature branches for each fix or group of related fixes
- **Commit Management**: Create meaningful commit messages with issue references
- **Merge Request Creation**: Generate detailed merge requests with before/after comparisons
- **Change Documentation**: Document all changes made for review

## Agent Architecture

### Class Structure
```python
class CodeHealerAgent(BaseAgent):
    def __init__(self, config):
        super().__init__(config, "CodeHealerAgent")
        self.git_client = GitClient(config)
        self.java_validator = JavaCodeValidator()
        self.backup_manager = BackupManager()
    
    def process(self, fix_plans: List[FixPlan]) -> Dict[str, Any]:
        # Main processing method
        
    def _read_and_analyze_code(self, fix_plan: FixPlan) -> CodeContext:
        # Read target file and analyze context
        
    def _generate_code_fix(self, fix_plan: FixPlan, context: CodeContext) -> CodeFix:
        # Generate actual code fix using LLM
        
    def _apply_fix_to_file(self, code_fix: CodeFix) -> bool:
        # Apply the fix to the actual file
        
    def _validate_fix(self, code_fix: CodeFix) -> ValidationResult:
        # Validate the applied fix
        
    def _create_git_branch_and_commit(self, fixes: List[CodeFix]) -> str:
        # Create Git branch and commit changes
```

## Fix Strategies

### 1. Try-with-Resources Pattern
**For**: Connection, Statement, ResultSet objects
**Strategy**: Convert manual resource management to try-with-resources
**Example**:
```java
// Before
Connection conn = DriverManager.getConnection(url);
Statement stmt = conn.createStatement();
// ... use connection
conn.close(); // Manual close

// After  
try (Connection conn = DriverManager.getConnection(url);
     Statement stmt = conn.createStatement()) {
    // ... use connection
} // Automatic close
```

### 2. Finally Block Pattern
**For**: Cases where try-with-resources isn't suitable
**Strategy**: Add proper finally block with null checks
**Example**:
```java
// Before
Connection conn = null;
try {
    conn = DriverManager.getConnection(url);
    // ... use connection
} catch (SQLException e) {
    // handle exception
}

// After
Connection conn = null;
try {
    conn = DriverManager.getConnection(url);
    // ... use connection
} catch (SQLException e) {
    // handle exception
} finally {
    if (conn != null) {
        try {
            conn.close();
        } catch (SQLException e) {
            // log error
        }
    }
}
```

### 3. Method Refactoring
**For**: Complex methods that need restructuring
**Strategy**: Extract resource management into separate methods
**Example**: Create utility methods for database operations

## LLM Prompt Engineering

### System Prompt Template
```
You are an expert Java developer specializing in fixing resource leak issues in Spring Boot applications.

Your task is to generate precise code fixes that:
1. Follow Java best practices and Spring Boot conventions
2. Properly handle resource management (Connections, Statements, ResultSets)
3. Maintain existing functionality while fixing the resource leak
4. Use appropriate patterns (try-with-resources or finally blocks)
5. Include proper error handling and logging

Generate ONLY the fixed code section, maintaining the same method signature and functionality.
```

### User Prompt Template
```
Fix this resource leak issue in Java code:

**Issue**: {issue_description}
**File**: {file_path}:{line_number}
**Problem**: {problem_analysis}
**Solution Strategy**: {solution_strategy}

**Current Code Context**:
```java
{code_context}
```

**Target Line** (line {line_number}):
```java
{target_line_content}
```

Please provide the fixed code that resolves the resource leak while maintaining all existing functionality.
```

## Validation and Quality Assurance

### 1. Syntax Validation
- **Java Compilation**: Attempt to compile the modified code
- **Import Validation**: Ensure all required imports are present
- **Method Signature**: Verify method signatures remain unchanged
- **Variable Scope**: Check variable declarations and scope

### 2. Functional Validation
- **Logic Preservation**: Ensure business logic remains intact
- **Exception Handling**: Verify exception handling is maintained or improved
- **Return Values**: Confirm method return values are preserved
- **Side Effects**: Check for unintended side effects

### 3. Code Quality Checks
- **Best Practices**: Ensure fixes follow Java and Spring Boot best practices
- **Code Style**: Maintain consistent code formatting and style
- **Performance**: Verify fixes don't introduce performance issues
- **Security**: Ensure fixes don't introduce security vulnerabilities

## Git Workflow

### 1. Branch Naming Convention
- **Single Fix**: `fix/sonar-{issue-key}-{short-description}`
- **Multiple Fixes**: `fix/sonar-batch-{timestamp}-resource-leaks`
- **Example**: `fix/sonar-fbf3862c-connection-resource-leak`

### 2. Commit Message Format
```
fix(sonar): resolve {issue-type} in {file-name}

- Issue: {issue-key}
- Type: {issue-severity} {issue-type}
- File: {file-path}:{line-number}
- Fix: {brief-description-of-fix}
- Confidence: {confidence-score}

Resolves SonarQube issue: {issue-key}
```

### 3. Merge Request Template
```markdown
## SonarQube Issue Fix

**Issue ID**: {issue-key}
**Severity**: {severity}
**Type**: {issue-type}
**Confidence**: {confidence-score}

### Problem
{problem-analysis}

### Solution
{solution-description}

### Files Changed
- `{file-path}` (line {line-number})

### Code Changes
#### Before
```java
{original-code}
```

#### After
```java
{fixed-code}
```

### Validation
- [x] Code compiles successfully
- [x] Functionality preserved
- [x] Resource leak resolved
- [x] Best practices followed

### Side Effects
{potential-side-effects}

### Testing
- Manual testing performed: {yes/no}
- Unit tests updated: {yes/no}
- Integration tests passed: {yes/no}
```

## Error Handling and Recovery

### 1. Fix Application Failures
- **Backup Restoration**: Restore original file from backup
- **Error Logging**: Log detailed error information
- **Partial Success**: Handle cases where some fixes succeed and others fail
- **User Notification**: Provide clear error messages and next steps

### 2. Validation Failures
- **Compilation Errors**: Report syntax issues and suggest manual review
- **Logic Errors**: Flag potential functional changes for human review
- **Quality Issues**: Report code quality concerns

### 3. Git Operation Failures
- **Branch Creation**: Handle branch naming conflicts
- **Commit Failures**: Manage commit conflicts and permissions
- **Merge Request**: Handle API failures and authentication issues

## Configuration and Settings

### 1. Fix Preferences
```python
class CodeHealerConfig:
    prefer_try_with_resources: bool = True
    max_fixes_per_branch: int = 10
    create_backup: bool = True
    validate_compilation: bool = True
    auto_create_mr: bool = True
    batch_similar_fixes: bool = True
```

### 2. Quality Thresholds
```python
class QualityThresholds:
    min_confidence_for_auto_fix: float = 0.8
    max_method_complexity_increase: int = 5
    require_manual_review_for_major_changes: bool = True
```

## Integration with Bug Hunter Agent

### 1. Data Flow
```
Bug Hunter Agent → FixPlan objects → Code Healer Agent → Applied Fixes
```

### 2. Communication Protocol
- **Input**: List of FixPlan objects from Bug Hunter Agent
- **Processing**: Sequential processing of each fix plan
- **Output**: Summary of applied fixes, created branches, and merge requests

### 3. Workflow Coordination
- **Sequential Execution**: Code Healer runs after Bug Hunter completes
- **Shared State**: Both agents share the same LangGraph workflow state
- **Error Propagation**: Errors in Code Healer don't affect Bug Hunter results

## Success Metrics and Reporting

### 1. Fix Success Rate
- **Applied Fixes**: Number of fixes successfully applied
- **Validation Success**: Number of fixes that pass validation
- **Compilation Success**: Number of fixes that compile correctly
- **Overall Success Rate**: Percentage of successful end-to-end fixes

### 2. Quality Metrics
- **Code Quality Improvement**: Reduction in SonarQube issues
- **Performance Impact**: Measure any performance changes
- **Maintainability**: Code complexity and readability metrics

### 3. Reporting Format
```json
{
  "session_id": "CodeHealerAgent_20251112_143022",
  "total_fix_plans": 10,
  "fixes_applied": 8,
  "fixes_validated": 7,
  "compilation_success": 7,
  "branches_created": 2,
  "merge_requests_created": 2,
  "success_rate": 0.7,
  "processing_time_seconds": 45.2,
  "errors": [
    {
      "issue_key": "abc123",
      "error": "Compilation failed after fix application",
      "action": "Reverted to original code"
    }
  ]
}
```

## Future Enhancements

### 1. Advanced Fix Strategies
- **Dependency Injection**: Convert manual resource management to Spring-managed beans
- **Aspect-Oriented Programming**: Use AOP for cross-cutting resource management concerns
- **Design Pattern Application**: Apply appropriate design patterns for resource management

### 2. Machine Learning Integration
- **Fix Pattern Learning**: Learn from successful fixes to improve future suggestions
- **Code Style Adaptation**: Adapt to project-specific coding styles and patterns
- **Quality Prediction**: Predict fix success probability before application

### 3. IDE Integration
- **Real-time Feedback**: Provide real-time feedback during development
- **Interactive Fixes**: Allow developers to review and modify fixes before application
- **Batch Operations**: Support bulk fix operations across multiple files

## Implementation Priority

### Phase 1: Core Functionality
1. Basic fix plan processing
2. Simple try-with-resources conversion
3. File backup and restoration
4. Basic Git integration

### Phase 2: Advanced Features
1. Complex fix strategies (finally blocks, method refactoring)
2. Comprehensive validation
3. Merge request automation
4. Error recovery mechanisms

### Phase 3: Quality and Performance
1. Advanced LLM prompt engineering
2. Code quality validation
3. Performance optimization
4. Comprehensive testing

This specification provides a complete blueprint for implementing the Code Healer Agent that will work seamlessly with the existing Bug Hunter Agent to provide end-to-end automated code fixing capabilities.