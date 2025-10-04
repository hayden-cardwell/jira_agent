# Setup Guide

This guide will walk you through setting up the development environment and creating a JIRA account to work with this Python JIRA agent.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Development Environment Setup](#development-environment-setup)
- [JIRA Account Setup](#jira-account-setup)
- [Configuration](#configuration)
- [Verification](#verification)
- [Troubleshooting](#troubleshooting)

## Prerequisites

Before getting started, ensure you have the following installed on your system:

- **Python**: Version 3.10 or higher
- **UV**: A high-performance Python package and project manager
- **Git**: For version control (optional but recommended)

## Development Environment Setup

### Installing UV

UV is a modern Python package and project manager that simplifies dependency management and virtual environments.

#### On macOS and Linux

Open your terminal and run:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

#### On Windows

Open PowerShell with administrative privileges and execute:

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

#### Verify Installation

After installation, verify UV is correctly installed:

```bash
uv --version
```

### Setting Up the Project

1. **Clone the Repository**:

   ```bash
   git clone <your-repo-url>
   cd jira_agent
   ```

2. **Install Dependencies**:

   UV will automatically create a virtual environment and install all required dependencies:

   ```bash
   uv sync
   ```

   This installs the following key packages:
   - `jira`: Official JIRA Python client for API interactions
   - `requests`: HTTP library for making API requests
   - `python-dotenv`: Secure environment variable management
   - `openai`: OpenAI Python client (also used for compatible APIs)
   - `boto3`: AWS SDK for Python (for Bedrock support)

3. **Verify Installation**:

   Check that all dependencies are correctly installed:

   ```bash
   uv run python -c "import jira, requests, dotenv; print('All dependencies installed successfully!')"
   ```

## JIRA Account Setup

To interact with JIRA APIs, you'll need either a JIRA Cloud account or access to a JIRA Server instance.

### Option 1: Free JIRA Cloud Account

1. **Create an Atlassian Account**:
   - Visit [Atlassian JIRA](https://www.atlassian.com/software/jira)
   - Click "Get it free" to create a free account
   - Provide your email, full name, and create a secure password
   - Verify your email address through the confirmation email

2. **Set Up Your JIRA Site**:
   - Choose a site name (e.g., `yourcompany.atlassian.net`)
   - Select "Software" as your product type
   - Create your first project (you can use the "Kanban" template for simplicity)

3. **Generate an API Token**:
   - Go to [Atlassian Account Settings](https://id.atlassian.com/manage-profile/security/api-tokens)
   - Click "Create API token"
   - Give it a descriptive label (e.g., "JIRA Agent Development")
   - Copy the generated token immediately (you won't be able to see it again)

### Option 2: JIRA Server/Data Center

If you're using a company JIRA Server or Data Center instance:

1. **Get Access**: Contact your JIRA administrator for access
2. **API Token**: Depending on your setup, you may need:
   - Personal Access Token (PAT) for Data Center
   - Username/password authentication for older Server versions
   - OAuth for more secure integrations

### Test Data Setup

For development and testing, create some sample data in your JIRA instance:

1. **Create a Test Project**:
   - Name: "Test Project" 
   - Key: "TEST"
   - Template: "Kanban software development"

2. **Add Sample Issues**:
   - Create 3-5 test tickets with different issue types (Story, Bug, Task)
   - Add various priorities and statuses
   - Include descriptions, comments, and attachments for realistic testing

## Configuration

### Environment Variables

1. **Copy the Example Environment File**:

   ```bash
   cp env.example .env
   ```

2. **Configure Your JIRA Credentials**:

   Edit the `.env` file with your specific values:

   ```ini
   # JIRA Configuration
   JIRA_SERVER=https://yourcompany.atlassian.net
   JIRA_EMAIL=your.email@example.com
   JIRA_API_TOKEN=your_generated_api_token
   JIRA_PROJECT_KEY=CSOPS
   ```

### Prompt files
Store editable prompt text in `prompts/` and point the agent at those files via `.env`:

```ini
PROMPT_TICKET_ANALYZER=./prompts/ticket_analyzer.prompt
PROMPT_CONFLUENCE_SEARCH=./prompts/confluence_search.prompt
```

The agent requires these files when it starts. If you customize the prompts, edit the `.prompt` files directly or update the paths to alternate files.

### Runtime Settings (optional)

These influence the live polling loop. Defaults are applied if unset.

```ini
# Poll every N seconds (default 30)
POLL_INTERVAL_SECONDS=30
# Look back N minutes for recently resolved tickets (default 300)
LOOKBACK_MINUTES=300
```

See the README Configuration section for the full list of supported variables (JIRA, Confluence, and LLM settings).

### LLM Provider Settings

The agent supports multiple LLM providers. Choose one:

#### Option A: OpenAI (Default)

```ini
LLM_PROVIDER=openai
OPENAI_API_KEY=your-openai-api-key
OPENAI_MODEL=gpt-4.1-2025-04-14
# Optional: custom endpoint for OpenAI-compatible APIs
OPENAI_BASE_URL=https://api.openai.com/v1
```

#### Option B: AWS Bedrock

```ini
LLM_PROVIDER=bedrock
AWS_REGION=us-east-1
BEDROCK_INFERENCE_PROFILE=us.anthropic.claude-3-5-haiku-20241022-v1:0
```

**AWS Bedrock Setup**:

1. **Request Model Access**:
   - Go to the [AWS Bedrock Console](https://console.aws.amazon.com/bedrock)
   - Navigate to "Model access" in the left sidebar
   - Click "Manage model access"
   - Enable access for Anthropic Claude models
   - Wait for access to be granted (usually instant)

2. **Configure AWS Credentials** (choose one method):
   
   **Method 1: Environment variables in .env**
   ```ini
   AWS_ACCESS_KEY_ID=your-access-key-id
   AWS_SECRET_ACCESS_KEY=your-secret-access-key
   ```
   
   **Method 2: AWS credentials file** (recommended)
   ```bash
   # Create/edit ~/.aws/credentials
   [default]
   aws_access_key_id = your-access-key-id
   aws_secret_access_key = your-secret-access-key
   ```
   
   **Method 3: IAM roles** (if running on AWS infrastructure)
   - No additional configuration needed
   - Ensure the role has `bedrock:InvokeModel` permission

3. **Available Inference Profiles**:
   - `us.anthropic.claude-3-5-sonnet-20241022-v2:0` - Most capable
   - `us.anthropic.claude-3-5-haiku-20241022-v1:0` - Faster and cheaper
   - `us.anthropic.claude-3-opus-20240229-v1:0` - Previous generation
   - Or create custom inference profiles in the Bedrock console

## Verification

### Test the Connection

Run the main script to verify everything is working:

```bash
uv run main.py
```

**Expected Output**:
```
INFO - LLM service initialized (OpenAI)
INFO - Confluence service initialized successfully
INFO - Agent initialization complete
INFO - Starting JIRA polling loop...
```

Or with Bedrock:
```
INFO - LLM service initialized (Bedrock: us.anthropic.claude-3-5-haiku-20241022-v1:0)
INFO - Confluence service initialized successfully
INFO - Agent initialization complete
INFO - Starting JIRA polling loop...
```

### Test API Access

You can also test specific JIRA operations:

```bash
# Test project access
uv run python -c "
from main import *
import os
from dotenv import load_dotenv
from jira import JIRA

load_dotenv()
jira = JIRA(server=os.getenv('JIRA_SERVER'), basic_auth=(os.getenv('JIRA_EMAIL'), os.getenv('JIRA_API_TOKEN')))
projects = jira.projects()
print(f'Available projects: {[p.key for p in projects]}')
"
```

