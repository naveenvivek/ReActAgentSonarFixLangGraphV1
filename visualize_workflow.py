#!/usr/bin/env python3
"""
Workflow visualization script for SonarQube AI Agent.
Displays the LangGraph workflow as a visual diagram.
"""

import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from sonar_ai_agent.config import Config
from sonar_ai_agent.workflows.bug_hunter_workflow import BugHunterWorkflow

def display_workflow_diagram():
    """Display the workflow diagram using different methods."""
    print("🎨 SonarQube AI Agent - Workflow Visualization")
    print("=" * 60)
    
    try:
        # Initialize workflow
        config = Config()
        workflow = BugHunterWorkflow(config)
        
        print("✅ Workflow initialized")
        
        # Method 1: Try to generate PNG using LangGraph
        print("\n🖼️ Attempting to generate PNG diagram...")
        try:
            png_data = workflow.draw_workflow_png()
            if png_data:
                # Save PNG file
                with open("bug_hunter_workflow.png", "wb") as f:
                    f.write(png_data)
                print("✅ PNG diagram saved as 'bug_hunter_workflow.png'")
                
                # Try to display if in Jupyter/IPython
                try:
                    from IPython.display import Image, display
                    display(Image(png_data))
                    print("✅ Diagram displayed inline")
                except ImportError:
                    print("ℹ️ Install IPython to display inline: pip install ipython")
                    print("📁 Open 'bug_hunter_workflow.png' to view the diagram")
            else:
                print("⚠️ Could not generate PNG diagram")
        except Exception as e:
            print(f"⚠️ PNG generation failed: {e}")
        
        # Method 2: Generate Mermaid text
        print("\n📝 Generating Mermaid diagram...")
        try:
            mermaid_text = workflow.get_mermaid_diagram()
            
            # Save Mermaid file
            with open("bug_hunter_workflow.mmd", "w") as f:
                f.write(mermaid_text)
            print("✅ Mermaid diagram saved as 'bug_hunter_workflow.mmd'")
            
            # Display Mermaid text
            print("\n🔍 Mermaid Diagram Code:")
            print("-" * 40)
            print(mermaid_text)
            
        except Exception as e:
            print(f"❌ Mermaid generation failed: {e}")
        
        # Method 3: Text visualization
        print("\n📊 Text Visualization:")
        print("-" * 40)
        text_viz = workflow.visualize_workflow()
        print(text_viz)
        
        print("\n🎯 Workflow Nodes Details:")
        print("-" * 40)
        nodes = [
            "1. Initialize - Start workflow and Langfuse tracking",
            "2. Prepare Repository - Clone/update SpringBootAppSonarAI",
            "3. Connect SonarQube - Validate connection to localhost:9100",
            "4. Fetch Issues - Get BLOCKER/CRITICAL/MAJOR issues",
            "5. Analyze Issue - Use Ollama LLM for analysis",
            "6. Create Fix Plan - Generate structured fix plan",
            "7. Update Langfuse - Track metrics and scores",
            "8. Finalize - Complete workflow and return results",
            "9. Handle Error - Error recovery and logging"
        ]
        
        for node in nodes:
            print(f"   {node}")
        
        print("\n🔗 Conditional Edges:")
        print("-" * 40)
        edges = [
            "• More Issues? → Continue analyzing next issue",
            "• All Done? → Finalize workflow",
            "• Error? → Handle error and cleanup",
            "• Repository Failed? → Error handler",
            "• SonarQube Failed? → Error handler"
        ]
        
        for edge in edges:
            print(f"   {edge}")
        
        print("\n💡 How to View Diagrams:")
        print("-" * 40)
        print("📁 PNG: Open 'bug_hunter_workflow.png' in image viewer")
        print("🌐 Mermaid: Copy 'bug_hunter_workflow.mmd' to https://mermaid.live")
        print("🔧 Online: Paste Mermaid code in Mermaid Live Editor")
        
    except Exception as e:
        print(f"❌ Visualization failed: {e}")
        return False
    
    return True

def create_jupyter_notebook():
    """Create a Jupyter notebook for interactive visualization."""
    notebook_content = '''
{
 "cells": [
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "# SonarQube AI Agent - Workflow Visualization\\n",
    "Interactive visualization of the LangGraph Bug Hunter workflow."
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {},
   "outputs": [],
   "source": [
    "import sys\\n",
    "from pathlib import Path\\n",
    "\\n",
    "# Add project root to path\\n",
    "project_root = Path.cwd()\\n",
    "sys.path.insert(0, str(project_root))\\n",
    "\\n",
    "from sonar_ai_agent.config import Config\\n",
    "from sonar_ai_agent.workflows.bug_hunter_workflow import BugHunterWorkflow\\n",
    "from IPython.display import Image, display"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {},
   "outputs": [],
   "source": [
    "# Initialize workflow\\n",
    "config = Config()\\n",
    "workflow = BugHunterWorkflow(config)\\n",
    "print(\\"✅ Workflow initialized\\")"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {},
   "outputs": [],
   "source": [
    "# Display workflow diagram\\n",
    "try:\\n",
    "    png_data = workflow.draw_workflow_png()\\n",
    "    if png_data:\\n",
    "        display(Image(png_data))\\n",
    "    else:\\n",
    "        print(\\"Could not generate PNG diagram\\")\\n",
    "except Exception as e:\\n",
    "    print(f\\"Error: {e}\\")"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {},
   "outputs": [],
   "source": [
    "# Display Mermaid diagram code\\n",
    "mermaid_text = workflow.get_mermaid_diagram()\\n",
    "print(\\"Mermaid Diagram Code:\\")\\n",
    "print(mermaid_text)"
   ]
  }
 ],
 "metadata": {
  "kernelspec": {
   "display_name": "Python 3",
   "language": "python",
   "name": "python3"
  },
  "language_info": {
   "codemirror_mode": {
    "name": "ipython",
    "version": 3
   },
   "file_extension": ".py",
   "name": "python",
   "nbconvert_exporter": "python",
   "pygments_lexer": "ipython3",
   "version": "3.8.0"
  }
 },
 "nbformat": 4,
 "nbformat_minor": 4
}
'''
    
    try:
        with open("workflow_visualization.ipynb", "w", encoding='utf-8') as f:
            f.write(notebook_content)
        print("✅ Jupyter notebook created: 'workflow_visualization.ipynb'")
        print("💡 Run: jupyter notebook workflow_visualization.ipynb")
        return True
    except Exception as e:
        print(f"❌ Failed to create notebook: {e}")
        return False

if __name__ == "__main__":
    print("🎨 SonarQube AI Agent - Workflow Visualization Tool")
    print("This script generates visual diagrams of the LangGraph workflow.\\n")
    
    # Generate visualizations
    success = display_workflow_diagram()
    
    if success:
        print("\\n📓 Creating Jupyter notebook for interactive visualization...")
        create_jupyter_notebook()
        
        print("\\n🎉 Visualization complete!")
        print("\\n📋 Files created:")
        print("   • bug_hunter_workflow.png - PNG diagram")
        print("   • bug_hunter_workflow.mmd - Mermaid source")
        print("   • workflow_visualization.ipynb - Jupyter notebook")
    else:
        print("\\n💡 To fix visualization issues:")
        print("1. Ensure all dependencies are installed")
        print("2. Check that the workflow initializes correctly")
        print("3. Install additional packages: pip install graphviz pillow")