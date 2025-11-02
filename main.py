#!/usr/bin/env python3
"""
SonarQube AI Agent - Main Entry Point
LangGraph-based Bug Hunter Agent with Langfuse integration.
"""

import sys
import logging
import argparse
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from sonar_ai_agent.config import Config
from sonar_ai_agent.workflows.bug_hunter_workflow import BugHunterWorkflow

def setup_logging(verbose: bool = False):
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

def main():
    """Main entry point for SonarQube AI Agent."""
    parser = argparse.ArgumentParser(
        description="SonarQube AI Agent - LangGraph Bug Hunter"
    )
    parser.add_argument(
        "--project-key", 
        help="SonarQube project key (overrides config)"
    )
    parser.add_argument(
        "--severities", 
        nargs="+", 
        default=["BLOCKER", "CRITICAL", "MAJOR"],
        help="Issue severities to process"
    )
    parser.add_argument(
        "--types", 
        nargs="+", 
        default=["BUG", "VULNERABILITY", "CODE_SMELL"],
        help="Issue types to process"
    )
    parser.add_argument(
        "--verbose", "-v", 
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.verbose)
    
    print("🤖 SonarQube AI Agent - LangGraph Bug Hunter")
    print("=" * 60)
    
    try:
        # Load configuration
        config = Config()
        print(f"✅ Configuration loaded")
        print(f"   - SonarQube: {config.sonar_url}")
        print(f"   - Project: {args.project_key or config.sonar_project_key}")
        print(f"   - Repository: {config.target_repo_url}")
        print(f"   - Model: {config.ollama_model}")
        print(f"   - Langfuse: {config.langfuse_url}")
        
        # Initialize workflow
        workflow = BugHunterWorkflow(config)
        print(f"✅ LangGraph workflow initialized")
        
        print(f"\n🔄 Running Bug Hunter Analysis...")
        print(f"   - Severities: {', '.join(args.severities)}")
        print(f"   - Types: {', '.join(args.types)}")
        print("-" * 40)
        
        # Run the workflow
        result = workflow.run(
            project_key=args.project_key,
            severities=args.severities,
            issue_types=args.types
        )
        
        # Display results
        print(f"\n📊 Analysis Results:")
        print("-" * 40)
        
        if result['status'] == 'success':
            print(f"✅ Status: {result['status']}")
            print(f"📝 Message: {result['message']}")
            print(f"📋 Fix Plans Created: {result['total_plans']}")
            print(f"⏱️ Processing Time: {result.get('processing_time', 0):.2f}s")
            
            # Show fix plans
            fix_plans = result.get('fix_plans', [])
            if fix_plans:
                print(f"\n📋 Fix Plans Summary:")
                print("-" * 40)
                for i, plan in enumerate(fix_plans, 1):
                    print(f"\n{i}. Issue: {plan.issue_key}")
                    print(f"   📁 File: {plan.file_path}:{plan.line_number}")
                    print(f"   🔍 Type: {plan.issue_description}")
                    print(f"   🎯 Confidence: {plan.confidence_score:.2f}")
                    print(f"   ⚡ Effort: {plan.estimated_effort}")
                    print(f"   💡 Analysis: {plan.problem_analysis[:100]}...")
                    print(f"   🔧 Solution: {plan.proposed_solution[:100]}...")
                
                print(f"\n🎯 Next Steps:")
                print("   - Review the fix plans above")
                print("   - Check Langfuse dashboard for detailed analytics")
                print("   - Implement the Code Healer Agent for automated fixes")
            else:
                print(f"\nℹ️ No issues found or processed")
                print("   - Check if SonarQube has issues for this project")
                print("   - Verify the severity and type filters")
        else:
            print(f"❌ Status: {result['status']}")
            print(f"💥 Error: {result['message']}")
            return 1
            
    except KeyboardInterrupt:
        print(f"\n⏹️ Analysis interrupted by user")
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1
    
    print(f"\n🎉 Bug Hunter analysis completed!")
    print("   Check Langfuse dashboard for detailed metrics and traces")
    return 0

if __name__ == "__main__":
    exit(main())
