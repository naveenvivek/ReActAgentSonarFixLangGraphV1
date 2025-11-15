#!/usr/bin/env python3
"""
Code Healer Workflow visualization script for SonarQube AI Agent.
Displays the LangGraph workflow as a visual diagram.
"""

from sonar_ai_agent.workflows.code_healer_workflow import CodeHealerWorkflow
from sonar_ai_agent.config import Config
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def display_code_healer_workflow_diagram():
    """Display the Code Healer workflow diagram using different methods."""
    print("🩹 SonarQube AI Agent - Code Healer Workflow Visualization")
    print("=" * 70)

    try:
        # Initialize workflow
        config = Config()
        workflow = CodeHealerWorkflow(config)

        print("✅ Code Healer Workflow initialized")

        # Method 1: Try to generate PNG using LangGraph
        print("\n🖼️ Attempting to generate PNG diagram...")
        try:
            png_data = workflow.draw_workflow_png()
            if png_data:
                # Save PNG file
                with open("code_healer_workflow.png", "wb") as f:
                    f.write(png_data)
                print("✅ PNG diagram saved as 'code_healer_workflow.png'")

                # Try to display if in Jupyter/IPython
                try:
                    from IPython.display import Image, display
                    display(Image(png_data))
                    print("✅ Diagram displayed inline")
                except ImportError:
                    print("ℹ️ Install IPython to display inline: pip install ipython")
                    print("📁 Open 'code_healer_workflow.png' to view the diagram")
            else:
                print("⚠️ Could not generate PNG diagram")
        except Exception as e:
            print(f"⚠️ PNG generation failed: {e}")

        # Method 2: Generate Mermaid text
        print("\n📝 Generating Mermaid diagram...")
        try:
            mermaid_text = workflow.get_mermaid_diagram()

            # Save Mermaid file
            with open("code_healer_workflow.mmd", "w") as f:
                f.write(mermaid_text)
            print("✅ Mermaid diagram saved as 'code_healer_workflow.mmd'")

            # Display Mermaid text
            print("\n🔍 Mermaid Diagram Code:")
            print("-" * 50)
            print(mermaid_text)

        except Exception as e:
            print(f"❌ Mermaid generation failed: {e}")

        # Method 3: Text visualization
        print("\n📊 Text Visualization:")
        print("-" * 50)
        text_viz = workflow.visualize_workflow()
        print(text_viz)

        print("\n🎯 Code Healer Workflow Nodes Details:")
        print("-" * 50)
        nodes = [
            "1. Initialize - Start workflow and metrics tracking",
            "2. Validate Fix Plans - Ensure input fix plans are valid",
            "3. Group Fixes - Organize fixes by file/similarity for batching",
            "4. Generate Code Fixes - Create actual code changes using LLM",
            "5. Validate Generated Fixes - Verify syntax and security of fixes",
            "6. Create Git Branch - Prepare version control branch",
            "7. Apply Fixes - Write changes to actual code files",
            "8. Create Merge Request - Prepare changes for review",
            "9. Finalize - Complete workflow and generate results",
            "10. Handle Error - Error recovery and cleanup"
        ]

        for node in nodes:
            print(f"   {node}")

        print("\n🔗 Conditional Edges:")
        print("-" * 50)
        edges = [
            "• More Fix Groups? → Continue processing next group",
            "• All Groups Done? → Finalize workflow",
            "• Error? → Handle error and cleanup",
            "• Fix Generation Failed? → Error handler",
            "• Git Operations Failed? → Error handler",
            "• Validation Failed? → Error handler"
        ]

        for edge in edges:
            print(f"   {edge}")

        print("\n📋 Workflow Characteristics:")
        print("-" * 50)
        characteristics = [
            "• Processes fix plans from Bug Hunter Agent",
            "• Groups similar fixes for efficient batch processing",
            "• Validates all generated code for syntax and security",
            "• Creates separate Git branches for each fix group",
            "• Automatically creates merge requests for review",
            "• Handles partial failures gracefully",
            "• Provides detailed logging and metrics",
            "• Supports rollback via Git version control"
        ]

        for char in characteristics:
            print(f"   {char}")

        print("\n💡 How to View Diagrams:")
        print("-" * 50)
        print("📁 PNG: Open 'code_healer_workflow.png' in image viewer")
        print("🌐 Mermaid: Copy 'code_healer_workflow.mmd' to https://mermaid.live")
        print("🔧 Online: Paste Mermaid code in Mermaid Live Editor")

        print("\n🔄 Integration with Bug Hunter:")
        print("-" * 50)
        print("• Bug Hunter creates fix plans → Code Healer applies them")
        print("• Use 'complete' mode to run both workflows together")
        print("• Standalone Code Healer requires fix plans as input")

    except Exception as e:
        print(f"❌ Visualization failed: {e}")
        return False

    return True


def create_code_healer_jupyter_notebook():
    """Create a Jupyter notebook for interactive Code Healer visualization."""
    notebook_content = '''
{
 "cells": [
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "# SonarQube AI Agent - Code Healer Workflow Visualization\\n",
    "Interactive visualization of the LangGraph Code Healer workflow."
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
    "from sonar_ai_agent.workflows.code_healer_workflow import CodeHealerWorkflow\\n",
    "from IPython.display import Image, display"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {},
   "outputs": [],
   "source": [
    "# Initialize Code Healer workflow\\n",
    "config = Config()\\n",
    "workflow = CodeHealerWorkflow(config)\\n",
    "print(\\"✅ Code Healer Workflow initialized\\")"
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
    "print(\\"Code Healer Workflow Mermaid Diagram:\\")\\n",
    "print(mermaid_text)"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {},
   "outputs": [],
   "source": [
    "# Display text visualization\\n",
    "text_viz = workflow.visualize_workflow()\\n",
    "print(text_viz)"
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
        with open("code_healer_workflow_visualization.ipynb", "w", encoding='utf-8') as f:
            f.write(notebook_content)
        print("✅ Jupyter notebook created: 'code_healer_workflow_visualization.ipynb'")
        print("💡 Run: jupyter notebook code_healer_workflow_visualization.ipynb")
        return True
    except Exception as e:
        print(f"❌ Failed to create notebook: {e}")
        return False


if __name__ == "__main__":
    print("🩹 SonarQube AI Agent - Code Healer Workflow Visualization Tool")
    print("This script generates visual diagrams of the Code Healer LangGraph workflow.\\n")

    # Generate visualizations
    success = display_code_healer_workflow_diagram()

    if success:
        print("\\n📓 Creating Jupyter notebook for interactive visualization...")
        create_code_healer_jupyter_notebook()

        print("\\n🎉 Code Healer Visualization complete!")
        print("\\n📋 Files created:")
        print("   • code_healer_workflow.png - PNG diagram")
        print("   • code_healer_workflow.mmd - Mermaid source")
        print("   • code_healer_workflow_visualization.ipynb - Jupyter notebook")
    else:
        print("\\n💡 To fix visualization issues:")
        print("1. Ensure all dependencies are installed")
        print("2. Check that the Code Healer workflow initializes correctly")
        print("3. Install additional packages: pip install graphviz pillow")
