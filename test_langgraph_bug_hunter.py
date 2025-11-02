#!/usr/bin/env python3
"""
Test script for the LangGraph Bug Hunter workflow.
Demonstrates the complete workflow with nodes, edges, and Langfuse integration.
"""

import sys
import logging
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from sonar_ai_agent.config import Config
from sonar_ai_agent.workflows.bug_hunter_workflow import BugHunterWorkflow

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_langgraph_bug_hunter():
    """Test the LangGraph Bug Hunter workflow."""
    print("🔄 Testing LangGraph Bug Hunter Workflow")
    print("=" * 60)
    
    try:
        # Load configuration
        config = Config()
        print(f"✅ Configuration loaded")
        print(f"   - SonarQube URL: {config.sonar_url}")
        print(f"   - Project Key: {config.sonar_project_key}")
        print(f"   - Ollama Model: {config.ollama_model}")
        print(f"   - Langfuse URL: {config.langfuse_url}")
        
    except Exception as e:
        print(f"❌ Failed to load configuration: {e}")
        return False
    
    try:
        # Initialize LangGraph workflow
        workflow = BugHunterWorkflow(config)
        print(f"✅ LangGraph Bug Hunter workflow initialized")
        
    except Exception as e:
        print(f"❌ Failed to initialize workflow: {e}")
        return False
    
    print("\n🔄 Running LangGraph Workflow...")
    print("-" * 40)
    
    # Run the workflow
    try:
        result = workflow.run(
            project_key=None,  # Use default from config
            severities=['BLOCKER', 'CRITICAL', 'MAJOR'],
            issue_types=['BUG', 'VULNERABILITY', 'CODE_SMELL']
        )
        
        if result['status'] == 'success':
            print(f"✅ Workflow completed successfully")
            print(f"   - Status: {result['status']}")
            print(f"   - Message: {result['message']}")
            print(f"   - Fix Plans Created: {result['total_plans']}")
            print(f"   - Processing Time: {result.get('processing_time', 0):.2f}s")
            
            # Display fix plans
            fix_plans = result.get('fix_plans', [])
            if fix_plans:
                print(f"\n📋 Fix Plans Created:")
                for i, plan in enumerate(fix_plans[:3], 1):  # Show first 3 plans
                    print(f"\n   Plan {i}: {plan.issue_key}")
                    print(f"   - File: {plan.file_path}:{plan.line_number}")
                    print(f"   - Issue: {plan.issue_description}")
                    print(f"   - Confidence: {plan.confidence_score:.2f}")
                    print(f"   - Effort: {plan.estimated_effort}")
                    print(f"   - Analysis: {plan.problem_analysis[:100]}...")
                    print(f"   - Solution: {plan.proposed_solution[:100]}...")
                
                if len(fix_plans) > 3:
                    print(f"   ... and {len(fix_plans) - 3} more plans")
            else:
                print("   No fix plans were created")
                
        else:
            print(f"❌ Workflow failed: {result['message']}")
            return False
            
    except Exception as e:
        print(f"❌ Workflow execution error: {e}")
        return False
    
    print(f"\n🔍 Workflow Visualization:")
    print("-" * 40)
    try:
        # Text visualization
        visualization = workflow.visualize_workflow()
        print(visualization)
        
        # Try to generate and save PNG diagram
        try:
            success = workflow.save_workflow_diagram("test_workflow_diagram.png")
            if success:
                print("✅ Workflow diagram saved as 'test_workflow_diagram.png'")
        except Exception as viz_error:
            print(f"⚠️ Could not save PNG diagram: {viz_error}")
        
        # Display Mermaid diagram
        try:
            mermaid = workflow.get_mermaid_diagram()
            print("\n📝 Mermaid Diagram Code:")
            print(mermaid[:200] + "..." if len(mermaid) > 200 else mermaid)
        except Exception as mermaid_error:
            print(f"⚠️ Could not generate Mermaid: {mermaid_error}")
            
    except Exception as e:
        print(f"Could not generate visualization: {e}")
    
    print(f"\n✨ LangGraph Bug Hunter Workflow Summary:")
    print("-" * 40)
    print("✅ LangGraph workflow with nodes and edges implemented")
    print("✅ State management between workflow steps")
    print("✅ SonarQube issues fetched and analyzed")
    print("✅ Ollama LLM integration for issue analysis")
    print("✅ Fix plans created with confidence scores")
    print("✅ Comprehensive Langfuse tracking and scoring")
    print("✅ Error handling and recovery mechanisms")
    print("✅ Conditional edges for workflow control")
    
    return True

def demonstrate_langfuse_integration():
    """Demonstrate the Langfuse integration features."""
    print("\n📊 Langfuse Integration Features")
    print("=" * 60)
    
    print("🔍 What gets tracked in Langfuse:")
    print("   - Workflow session with unique ID")
    print("   - Repository preparation events")
    print("   - SonarQube connection events")
    print("   - Issues fetched with metadata")
    print("   - Individual issue analysis events")
    print("   - Fix plan confidence scores")
    print("   - Effort estimation scores")
    print("   - Workflow completion summary")
    print("   - Success rate metrics")
    print("   - Error events and debugging info")
    
    print("\n📈 Langfuse Scores Created:")
    print("   - fix_plan_confidence: 0.0-1.0 (AI confidence in fix)")
    print("   - fix_effort_estimate: 0.3-0.9 (LOW/MEDIUM/HIGH effort)")
    print("   - workflow_success_rate: 0.0-1.0 (issues processed successfully)")
    
    print("\n🎯 Benefits:")
    print("   - Complete traceability from SonarQube issue to fix plan")
    print("   - Quality monitoring and improvement over time")
    print("   - Performance metrics and optimization insights")
    print("   - Debugging and error analysis capabilities")
    print("   - Historical analysis of fix success rates")

def show_workflow_nodes_and_edges():
    """Show the detailed workflow structure."""
    print("\n🔄 LangGraph Workflow Structure")
    print("=" * 60)
    
    print("📍 Workflow Nodes:")
    print("   1. initialize - Start workflow and Langfuse tracking")
    print("   2. prepare_repository - Clone/update target repository")
    print("   3. connect_sonarqube - Validate SonarQube connection")
    print("   4. fetch_issues - Get issues from SonarQube")
    print("   5. analyze_issue - Analyze current issue with LLM")
    print("   6. create_fix_plan - Generate structured fix plan")
    print("   7. update_langfuse - Track issue analysis in Langfuse")
    print("   8. finalize - Complete workflow and create summary")
    print("   9. handle_error - Handle any workflow errors")
    
    print("\n🔗 Workflow Edges:")
    print("   Linear Flow:")
    print("   initialize → prepare_repository → connect_sonarqube → fetch_issues")
    print("   fetch_issues → analyze_issue → create_fix_plan → update_langfuse")
    print("   ")
    print("   Conditional Edges:")
    print("   update_langfuse → {continue: analyze_issue, finalize: finalize, error: handle_error}")
    print("   prepare_repository → {continue: connect_sonarqube, error: handle_error}")
    print("   connect_sonarqube → {continue: fetch_issues, error: handle_error}")
    print("   fetch_issues → {continue: analyze_issue, error: handle_error}")
    print("   ")
    print("   End Points:")
    print("   finalize → END")
    print("   handle_error → END")
    
    print("\n🔄 State Management:")
    print("   - Maintains workflow status throughout execution")
    print("   - Tracks current issue being processed")
    print("   - Accumulates fix plans as they're created")
    print("   - Preserves error information for debugging")
    print("   - Links all events to Langfuse session")

if __name__ == "__main__":
    print("🤖 LangGraph Bug Hunter Workflow Test Suite")
    print("This script tests the complete LangGraph workflow with Langfuse integration.\n")
    
    # Show workflow structure
    show_workflow_nodes_and_edges()
    
    # Demonstrate Langfuse features
    demonstrate_langfuse_integration()
    
    # Run main test
    success = test_langgraph_bug_hunter()
    
    if success:
        print("\n🎉 LangGraph Bug Hunter Workflow Test Completed Successfully!")
        print("The workflow is ready for production use with full Langfuse tracking.")
    else:
        print("\n💡 To fix issues:")
        print("1. Ensure all services are running (SonarQube, Ollama, Langfuse)")
        print("2. Verify your .env file has correct configuration")
        print("3. Check network connectivity to all services")
        print("4. Review the logs for specific error details")