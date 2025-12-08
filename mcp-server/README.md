# Denial Intelligence MCP Server

Azure Functions-based Model Context Protocol (MCP) server that exposes 42+ AI agents for denial management as MCP tools for Azure AI Foundry Agent Service.

## Overview

This MCP server enables Azure AI Foundry agents to access the full suite of denial intelligence agents through the Model Context Protocol. Each agent is exposed as an MCP tool with proper input/output schemas.

## Agent Categories

| Category | Count | Description |
|----------|-------|-------------|
| Denial Management | 12 | Core denial analysis and appeal optimization |
| Validation Layer | 6 | Multi-model verification for safety-critical decisions |
| CFO Intelligence | 12 | Financial forecasting and churn prediction |
| Status Intelligence | 8 | 277CA/835 status tracking and analysis |
| System Agents | 3 | Audit, health monitoring, and policy scraping |
| RAG Agents | 1 | Policy retrieval and validation |

## Agents

### Denial Management Agents (DEN-001 to DEN-012)
- **DEN-001 SDOH Scorer** (gpt-4.1): Scores social determinants of health impact
- **DEN-002 Care Gap Detector** (gpt-4.1): Identifies gaps in patient care
- **DEN-003 Clinical Urgency** (gpt-4.1): Assesses clinical urgency of cases
- **DEN-004 Financial Value** (gpt-4.1-mini): Calculates financial value of claims
- **DEN-005 Recovery Predictor** (o3): Predicts recovery likelihood
- **DEN-006 P2P Optimizer** (deepseek): Optimizes peer-to-peer reviews
- **DEN-007 Queue Wait Time** (gpt-4.1-nano): Estimates queue wait times
- **DEN-008 PA Risk Predictor** (gpt-4.1-mini): Predicts prior auth risk
- **DEN-009 Doc Completeness** (gpt-4.1-mini): Checks documentation completeness
- **DEN-010 Policy Monitor** (gpt-4.1-nano): Monitors policy changes
- **DEN-011 Root Cause Analyzer** (o3): Analyzes root causes of denials
- **DEN-012 Staff Feedback Processor** (deepseek): Processes staff feedback for RL

### Validation Agents (VAL-001 to VAL-006)
- **VAL-001 Safety Validator** (o1): Validates safety-critical decisions
- **VAL-002 Consensus Checker** (gpt-4.1): Checks agent consensus
- **VAL-003 Policy Match Grader** (deepseek): Grades policy compliance
- **VAL-004 Viability Scorer** (o3): Scores appeal viability
- **VAL-005 Eligibility Verifier** (gpt-4.1-mini): Verifies patient eligibility
- **VAL-006 Followup Scheduler** (gpt-4.1-nano): Schedules follow-up actions

### CFO Intelligence Agents (CFO-001 to CFO-012)
- **CFO-001 Submission Churn Predictor** (o3): Predicts submission churn
- **CFO-002 Payer Behavior Modeler** (gpt-4.1): Models payer behavior patterns
- **CFO-003 Procedure Risk Scorer** (gpt-4.1): Scores procedure denial risk
- **CFO-004 Documentation Gap Predictor** (gpt-4.1-mini): Predicts documentation gaps
- **CFO-005 Contractual Estimator** (gpt-4.1): Estimates contractual amounts
- **CFO-006 Collection Timeline Predictor** (gpt-4.1-mini): Predicts collection timelines
- **CFO-007 Variance Analyzer** (gpt-4.1): Analyzes payment variances
- **CFO-008 Denial Categorizer** (gpt-4.1-mini): Categorizes denial types
- **CFO-009 Reconciliation Scorer** (gpt-4.1-mini): Scores reconciliation accuracy
- **CFO-010 Cash Flow Forecaster** (gpt-4.1): Forecasts cash flow
- **CFO-011 Budget Scenario Modeler** (o3): Models budget scenarios
- **CFO-012 Executive Narrative Generator** (gpt-4.1): Generates executive narratives

### Status Intelligence Agents (STS-001 to STS-008)
- **STS-001 Front End Rejection Analyzer** (o3): Analyzes 277CA front-end rejections
- **STS-002 Appeal Deadline Risk Assessor** (o3): Prioritizes appeals by deadline risk
- **STS-003 Pending Claim Risk Scorer** (gpt-4.1): Scores risk for pending claims
- **STS-004 Aging Trend Forecaster** (gpt-4.1): Forecasts A/R aging trends
- **STS-005 Payer SLA Monitor** (gpt-4.1-mini): Monitors payer SLA compliance
- **STS-006 COB Coordination Analyzer** (gpt-4.1-mini): Analyzes COB coordination issues
- **STS-007 Status Pattern Detector** (deepseek): Detects status flow anomalies
- **STS-008 Status Intelligence Summarizer** (gpt-4.1-nano): Summarizes status intelligence

### System Agents (SYS-001 to SYS-003)
- **SYS-001 Audit Agent** (o3): Out-of-band consistency validation
- **SYS-002 Health Check Agent** (gpt-4.1-mini): Monitors agent health/performance
- **SYS-003 Policy Scraper Agent** (gpt-4.1): Weekly automated scraping of FL payer policy portals

### RAG Agents (RAG-001)
- **RAG-001 Policy RAG Agent** (gpt-4.1): Retrieves and validates claims against payer policies

## Deployment

### Prerequisites
- Azure subscription with Azure AI Foundry access
- Azure Functions Core Tools v4
- Python 3.11+

### Deploy to Azure

1. Copy `.env.example` to `.env` and configure:
```bash
cp .env.example .env
# Edit .env with your Azure credentials
```

2. Deploy using Azure CLI:
```bash
# Deploy infrastructure
az deployment group create \
  --resource-group rg-gregorykatz-2103 \
  --template-file ../infra/mcp-function-deploy.bicep \
  --parameters projectEndpoint=https://pharma-agents-jnj-resource.services.ai.azure.com

# Deploy function code
func azure functionapp publish denial-intelligence-mcp
```

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Start local server
func start
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/mcp` | GET | Tool discovery - returns all available tools |
| `/api/mcp` | POST | Execute a tool with arguments |
| `/api/mcp/tools` | GET | List all tools with count |
| `/api/mcp/tools/{name}` | GET | Get specific tool details |
| `/api/mcp/execute` | POST | Execute a tool |
| `/api/mcp/categories` | GET | List all agent categories |
| `/api/mcp/categories/{cat}` | GET | Get tools by category |
| `/api/health` | GET | Health check |

## Usage with Azure AI Foundry

```python
from azure.ai.projects import AIProjectClient
from azure.ai.agents.models import McpTool
from azure.identity import DefaultAzureCredential

# Initialize client
project_client = AIProjectClient(
    endpoint=os.environ["PROJECT_ENDPOINT"],
    credential=DefaultAzureCredential(),
)

# Create MCP tool pointing to this server
mcp_tool = McpTool(
    server_label="denial-intelligence",
    server_url="https://denial-intelligence-mcp.azurewebsites.net/api/mcp",
    allowed_tools=["sdoh_scorer", "recovery_predictor", "clinical_urgency"]
)

# Create agent with MCP tools
with project_client:
    agents_client = project_client.agents
    agent = agents_client.create_agent(
        model="gpt-4.1",
        name="denial-management-agent",
        instructions="You are a denial management assistant with access to 42+ specialized AI agents.",
        tools=mcp_tool.definitions,
    )
```

## Configuration

### Environment Variables

| Variable | Description |
|----------|-------------|
| `PROJECT_ENDPOINT` | Azure AI Foundry project endpoint |
| `SUBSCRIPTION_ID` | Azure subscription ID |
| `RESOURCE_GROUP` | Azure resource group |
| `PROJECT_NAME` | Azure AI Foundry project name |
| `AZURE_SEARCH_ENDPOINT` | Azure AI Search endpoint for RAG |
| `AZURE_SEARCH_INDEX_NAME` | Search index name |
| `LOG_LEVEL` | Logging level (INFO, DEBUG, etc.) |

## Architecture

```
Azure AI Foundry Agent
        |
        v
    MCP Protocol
        |
        v
+-------------------+
| MCP Server        |
| (Azure Functions) |
+-------------------+
        |
        v
+-------------------+
| Agent Registry    |
| (42+ Agents)      |
+-------------------+
        |
        v
+-------------------+
| Backend Services  |
| - AI Models       |
| - Azure AI Search |
| - Azure SQL       |
+-------------------+
```

## License

Proprietary - Denial Intelligence Platform
