# 🤖 SonarQube AI Agent with LangGraph

An intelligent code quality automation system that uses LangGraph workflows and local LLMs to analyze SonarQube issues and create AI-powered fix plans.

## ✨ Features

- 🔄 **LangGraph Workflow Orchestration** - 9-node workflow with conditional edges
- 🤖 **AI-Powered Analysis** - Uses AWS Bedrock LLM for intelligent issue analysis
- 🔍 **SonarQube Integration** - Fetches and prioritizes code quality issues
- 📊 **File-based Logging** - Complete tracking and quality metrics with log rotation
- 🎨 **Workflow Visualization** - Interactive Mermaid diagrams
- 📁 **Git Integration** - Repository cloning and code context extraction
- ⚡ **Production Ready** - Comprehensive error handling and recovery

## 🏗️ Architecture

```mermaid
graph TD
    A[Initialize] --> B[Prepare Repository]
    B --> C[Connect SonarQube]
    C --> D[Fetch Issues]
    D --> E[Analyze Issue]
    E --> F[Create Fix Plan]
    F --> G[Log Results]
    G --> H{More Issues?}
    H -->|Yes| E
    H -->|No| I[Finalize]
    
    B --> J[Handle Error]
    C --> J
    D --> J
    E --> J
    F --> J
    G --> J
    
    I --> K[END]
    J --> K
```

## 🚀 Quick Start

### Prerequisites

1. **SonarQube Server** running on `localhost:9100`
2. **AWS Bedrock** access with appropriate credentials and model access
3. **Log directory** with write permissions for file-based logging

### Installation

```bash
# Clone the repository
git clone https://gitlab.com/naveenvivek/ReActAgentSonarFixLangGraph.git
cd ReActAgentSonarFixLangGraph

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Configuration

Create a `.env` file with your settings:

```bash
# SonarQube Configuration
SONAR_URL=http://localhost:9100
SONAR_TOKEN=your_sonar_token_here
SONAR_PROJECT_KEY=your_project_key

# Target Repository
TARGET_REPO_URL=https://gitlab.com/your-username/your-repo
TARGET_REPO_PATH=/path/to/local/repo
TARGET_REPO_BRANCH=main

# AI Configuration
# AWS Bedrock Configuration
AWS_ACCESS_KEY_ID=your-aws-access-key
AWS_SECRET_ACCESS_KEY=your-aws-secret-key
BEDRock_MODEL_ID=amazon.nova-2-multimodal-embeddings-v1:0
AWS_REGION=us-east-1

# Logging Configuration
LOG_LEVEL=INFO
LOG_FILE=logs/sonar_ai_agent.log
LOG_MAX_SIZE=10485760
LOG_BACKUP_COUNT=5

# Git Configuration
GIT_USER_NAME=Your Name
GIT_USER_EMAIL=your.email@example.com

# GitLab Configuration
GITLAB_URL=https://gitlab.com
GITLAB_TOKEN=glpat-your-gitlab-token-here
GITLAB_PROJECT_ID=your-project-id
```

### Run the Agent

```bash
# Basic run
python main.py

# With custom options
python main.py --severities BLOCKER CRITICAL --verbose

# Run tests
python test_langgraph_bug_hunter.py

# Generate workflow visualization
python visualize_workflow.py
```

## 📊 What It Does

1. **🔗 Connects** to your SonarQube server
2. **📁 Clones** your target repository locally
3. **📊 Fetches** code quality issues (BLOCKER, CRITICAL, MAJOR)
4. **🤖 Analyzes** each issue using AWS Bedrock LLM
5. **📋 Creates** structured fix plans with confidence scores
6. **📈 Tracks** everything in structured log files with rotation
7. **🎨 Visualizes** the complete workflow

## 🏗️ Project Structure

```
sonar_ai_agent/
├── agents/
│   ├── base_agent.py           # Base agent with AWS Bedrock & file logging
│   └── bug_hunter_agent.py     # Main Bug Hunter Agent
├── integrations/
│   ├── sonarqube_client.py     # SonarQube API client
│   └── gitlab_client.py        # GitLab operations
├── workflows/
│   └── bug_hunter_workflow.py  # LangGraph workflow
├── config.py                   # Configuration management
└── models.py                   # Data models
```

## 🎯 Example Output

```
🤖 SonarQube AI Agent - LangGraph Bug Hunter
============================================================
✅ Configuration loaded
✅ LangGraph workflow initialized

🔄 Running Bug Hunter Analysis...
----------------------------------------
✅ Repository prepared successfully
✅ SonarQube connection validated
✅ Fetched and prioritized 3 issues
✅ Issue analysis completed
✅ Fix plan created with confidence: 0.95

📋 Fix Plans Summary:
----------------------------------------
1. Issue: BLOCKER VULNERABILITY
   📁 File: pom.xml:28
   🎯 Confidence: 0.95
   ⚡ Effort: HIGH
   💡 Analysis: Hardcoded token security vulnerability
   🔧 Solution: Use environment variables for sensitive data

🎉 Bug Hunter analysis completed!
```

## 🔧 CLI Options

```bash
# Analyze specific severities
python main.py --severities BLOCKER CRITICAL

# Focus on specific issue types
python main.py --types BUG VULNERABILITY

# Use different project
python main.py --project-key "my-other-project"

# Enable verbose logging
python main.py --verbose

# Combine options
python main.py --severities BLOCKER --types BUG --verbose
```

## 🎨 Workflow Visualization

Generate interactive workflow diagrams:

```bash
# Generate all visualizations
python visualize_workflow.py

# View in Jupyter
jupyter notebook workflow_visualization.ipynb

# View online at https://mermaid.live
# (copy content from bug_hunter_workflow.mmd)
```

## 📊 Logging and Observability

The system provides comprehensive tracking through structured file logging:

- **Session Tracking** - Unique session IDs for each run
- **Quality Metrics** - Fix plan confidence scores
- **Performance Metrics** - Processing time and success rates
- **Error Tracking** - Complete error logging and debugging
- **Traceability** - From SonarQube issue to fix plan

## 🔧 Configuration Options

### SonarQube Settings
- `SONAR_URL` - SonarQube server URL
- `SONAR_TOKEN` - Authentication token
- `SONAR_PROJECT_KEY` - Project to analyze

### AI Settings
- `AWS_ACCESS_KEY_ID` - AWS access key
- `AWS_SECRET_ACCESS_KEY` - AWS secret key
- `BEDROCK_MODEL_ID` - AWS Bedrock model to use
- `AWS_REGION` - AWS region

### Repository Settings
- `TARGET_REPO_URL` - Git repository URL
- `TARGET_REPO_PATH` - Local repository path
- `TARGET_REPO_BRANCH` - Branch to analyze

## 🧪 Testing

```bash
# Run the complete test suite
python test_langgraph_bug_hunter.py

# Test with specific parameters
python main.py --severities BLOCKER --verbose
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if needed
5. Submit a merge request

## 📝 License

This project is licensed under the MIT License.

## 🙏 Acknowledgments

- **LangGraph** for workflow orchestration
- **AWS Bedrock** for cloud LLM inference
- **File-based Logging** for observability and debugging
- **SonarQube** for code quality analysis

## 🔗 Links

- [Repository](https://gitlab.com/naveenvivek/ReActAgentSonarFixLangGraph)
- [SonarQube Documentation](https://docs.sonarqube.org/)
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [AWS Bedrock Documentation](https://docs.aws.amazon.com/bedrock/)


---

**Built with ❤️ for intelligent code quality automation**