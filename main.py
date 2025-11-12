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
from sonar_ai_agent.workflows.complete_workflow import CompleteSonarWorkflow

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
    parser.add_argument(
        "--mode", 
        choices=["bug-hunter", "complete"],
        default="bug-hunter",
        help="Execution mode: bug-hunter (analysis only) or complete (analysis + fixes)"
    )
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.verbose)
    
    print("[AI] SonarQube AI Agent - LangGraph Bug Hunter")
    print("=" * 60)
    
    try:
        # Load configuration
        config = Config()
        print(f"[SUCCESS] Configuration loaded")
        print(f"   - SonarQube: {config.sonar_url}")
        print(f"   - Project: {args.project_key or config.sonar_project_key}")
        print(f"   - Repository: {config.target_repo_url}")
        print(f"   - Model: {config.ollama_model}")
        print(f"   - Log File: {config.log_file}")
        
        # Initialize workflow based on mode
        if args.mode == "complete":
            workflow = CompleteSonarWorkflow(config)
            print(f"[SUCCESS] Complete LangGraph workflow initialized (Bug Hunter + Code Healer)")
            
            print(f"\n[PROCESS] Running Complete Analysis and Fix Application...")
            print(f"   - Severities: {', '.join(args.severities)}")
            print(f"   - Mode: Analysis + Automated Fixes")
            print("-" * 40)
            
            # Run complete workflow
            result = workflow.run(
                project_key=args.project_key or config.sonar_project_key,
                severities=args.severities
            )
        else:
            workflow = BugHunterWorkflow(config)
            print(f"[SUCCESS] Bug Hunter LangGraph workflow initialized")
            
            print(f"\n[PROCESS] Running Bug Hunter Analysis...")
            print(f"   - Severities: {', '.join(args.severities)}")
            print(f"   - Types: {', '.join(args.types)}")
            print("-" * 40)
            
            # Run bug hunter workflow
            result = workflow.run(
                project_key=args.project_key,
                severities=args.severities,
                issue_types=args.types
            )
        
        # Display results based on mode
        if args.mode == "complete":
            print(f"\n[DATA] Complete Workflow Results:")
            print("-" * 40)
            
            metadata = result.get('metadata', {})
            print(f"[SUCCESS] Workflow Status: {metadata.get('workflow_status', 'unknown')}")
            print(f"[LIST] Issues Processed: {metadata.get('total_issues', 0)}")
            print(f"[LIST] Fix Plans Generated: {metadata.get('fix_plans_generated', 0)}")
            print(f"[LIST] Fixes Applied: {metadata.get('fixes_applied', 0)}")
            print(f"[LIST] Successful Fixes: {metadata.get('successful_fixes', 0)}")
            print(f"[LIST] Merge Requests Created: {metadata.get('merge_requests_created', 0)}")
            print(f"[TARGET] Overall Success Rate: {metadata.get('overall_success_rate', 0):.2%}")
            
            # Show merge requests
            merge_requests = result.get('merge_requests', [])
            if merge_requests:
                print(f"\n[LIST] Created Merge Requests:")
                for i, mr_url in enumerate(merge_requests, 1):
                    print(f"   {i}. {mr_url}")
            
            # Show errors if any
            errors = result.get('errors', [])
            if errors:
                print(f"\n[WARNING] Errors Encountered:")
                for error in errors[:5]:  # Show first 5 errors
                    print(f"   - {error}")
                if len(errors) > 5:
                    print(f"   ... and {len(errors) - 5} more errors")
        else:
            print(f"\n[DATA] Analysis Results:")
            print("-" * 40)
            
            if result['status'] == 'success':
                print(f"[SUCCESS] Status: {result['status']}")
                print(f"[LIST] Message: {result['message']}")
                print(f"[LIST] Fix Plans Created: {result['total_plans']}")
                print(f"[TIME] Processing Time: {result.get('processing_time', 0):.2f}s")
            
                # Show fix plans for bug hunter mode
                fix_plans = result.get('fix_plans', [])
                if fix_plans:
                    print(f"\n[LIST] Fix Plans Summary:")
                    print("-" * 40)
                    for i, plan in enumerate(fix_plans, 1):
                        print(f"\n{i}. Issue: {plan.issue_key}")
                        print(f"   [FOLDER] File: {plan.file_path}:{plan.line_number}")
                        print(f"   [SEARCH] Type: {plan.issue_description}")
                        print(f"   [TARGET] Confidence: {plan.confidence_score:.2f}")
                        print(f"   [EFFORT] Effort: {plan.estimated_effort}")
                        
                        # Safely truncate analysis and solution
                        analysis = str(plan.problem_analysis) if plan.problem_analysis else "No analysis available"
                        solution = str(plan.proposed_solution) if plan.proposed_solution else "No solution available"
                        
                        analysis_preview = analysis[:150] + "..." if len(analysis) > 150 else analysis
                        solution_preview = solution[:150] + "..." if len(solution) > 150 else solution
                        
                        print(f"   [IDEA] Analysis: {analysis_preview}")
                        print(f"   [FIX] Solution: {solution_preview}")
                        
                        # Show side effects if any
                        if plan.potential_side_effects and any(plan.potential_side_effects):
                            side_effects = [str(effect) for effect in plan.potential_side_effects if effect]
                            if side_effects:
                                print(f"   [WARNING] Side Effects: {', '.join(side_effects[:2])}")
                        
                        print(f"   [DATA] Full details logged to: {config.log_file}")
                    
                    print(f"\n[TARGET] Next Steps:")
                    print("   - Review the fix plans above")
                    print(f"   - Check log file for detailed analytics: {config.log_file}")
                    print("   - Run with --mode complete to apply fixes automatically")
                else:
                    print(f"\n[INFO] No issues found or processed")
                    print("   - Check if SonarQube has issues for this project")
                    print("   - Verify the severity and type filters")
            else:
                print(f"[ERROR] Status: {result['status']}")
                print(f"[ERROR] Error: {result['message']}")
                return 1
            
    except KeyboardInterrupt:
        print(f"\n[STOP] Analysis interrupted by user")
        return 1
    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1
    
    if args.mode == "complete":
        print(f"\n[SUCCESS] Complete workflow finished!")
        print(f"   - Analysis and fix application completed")
        print(f"   - Check merge requests for code review")
    else:
        print(f"\n[SUCCESS] Bug Hunter analysis completed!")
        print(f"   - Run with --mode complete to apply fixes")
    
    print(f"   Check log file for detailed metrics and traces: {config.log_file}")
    return 0

if __name__ == "__main__":
    exit(main())
