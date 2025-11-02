#!/usr/bin/env python3
"""
Simple script to display workflow diagram.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from sonar_ai_agent.config import Config
from sonar_ai_agent.workflows.bug_hunter_workflow import BugHunterWorkflow

def show_workflow():
    """Display workflow diagram."""
    print("🎨 Displaying Bug Hunter Workflow")
    
    try:
        # Initialize workflow
        config = Config()
        workflow = BugHunterWorkflow(config)
        
        # Generate and save PNG
        png_data = workflow.draw_workflow_png()
        if png_data:
            with open("current_workflow.png", "wb") as f:
                f.write(png_data)
            print("✅ Workflow diagram saved as 'current_workflow.png'")
            
            # Try to display inline (if in Jupyter)
            try:
                from IPython.display import Image, display
                display(Image(png_data))
                print("✅ Diagram displayed inline")
            except ImportError:
                print("📁 Open 'current_workflow.png' to view the diagram")
        
        # Show Mermaid code
        mermaid = workflow.get_mermaid_diagram()
        print("\n📝 Mermaid Code:")
        print(mermaid)
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    show_workflow()