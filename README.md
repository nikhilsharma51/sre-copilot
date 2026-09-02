# SRE Copilot

**Autonomous AI agent for production incident response and remediation**

## Overview

SRE Copilot is an AI-powered agent system that automates the response to production incidents. When an alert is triggered, the system autonomously investigates the root cause using available data sources, proposes a remediation action, validates it against safety constraints, and then executes it upon human approval. This workflow reduces mean-time-to-resolution (MTTR) from 10+ minutes to 1-2 minutes while maintaining human oversight over critical decisions.

## Key Features

- **Autonomous Investigation**: Uses LLM-driven agents to gather logs, metrics, and disk usage data from services
- **Root Cause Analysis**: Generates confidence-scored hypotheses about the underlying problem
- **Intelligent Remediation**: Proposes contextually appropriate fixes from a set of safe, pre-approved actions
- **Safety Guardrails**: Enforces hard deny-lists, whitelisting by service, and rate limiting per incident
- **Human-in-the-Loop**: Requires explicit human approval before executing any remediation action
- **Incident Resumption**: Persists agent state to SQLite, allowing workflows to pause for approval and resume later
- **Full Audit Trail**: Records every step of the incident lifecycle in a timeline
- **Multi-Severity Routing**: P1 alerts trigger immediate Slack notification; P3 alerts proceed directly to investigation

## Tech Stack

**Backend & AI/ML**
- Python 3.11
- LangGraph 1.2.11 (workflow orchestration)
- LangChain 0.22+ (LLM framework)
- Groq API (LLM inference)
- Pydantic 2.13+ (data validation & structured outputs)

**Agent Tooling**
- Model Context Protocol (MCP) 1.29+ (tool abstraction layer)
- FastMCP 3.4.7 (MCP server implementation)

**Database & Persistence**
- SQLite (incident state checkpointing)
- AsyncSqliteSaver (async checkpoint storage via LangGraph)
- aiosqlite 0.22+ (async SQLite driver)

**External Integrations**
- GitHub MCP Server (PR creation for reversions)
- Slack MCP Server (incident notifications)
- LangSmith (optional tracing & debugging)

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   INCIDENT ALERT                            │
│        (checkout error rate / disk usage critical)           │
└──────────────────────┬──────────────────────────────────────┘
                       │
          ┌────────────▼────────────┐
          │  route_by_severity()    │
          │  P1 → notify + triage   │
          │  P3 → triage            │
          └────────────┬────────────┘
                       │
          ┌────────────▼────────────┐
          │  TRIAGE SUBGRAPH        │
          │  ├─ triage_agent()      │◄─── Calls LLM with tools
          │  ├─ tools (get_logs,    │
          │  │  get_metrics,        │
          │  │  get_disk_usage)     │
          │  └─ summarize_          │
          │     hypothesis()        │
          └────────────┬────────────┘
                       │
          ┌────────────▼────────────┐
          │ propose_remediation()   │◄─── LLM selects action
          └────────────┬────────────┘
                       │
          ┌────────────▼────────────┐
          │  guardrail_check()      │◄─── Verify safety
          └────────────┬────────────┘
                       │
        ┌──────────────┴──────────────┐
        │                             │
   Allowed                        Blocked
        │                             │
   ┌────▼──────────┐          ┌───────▼────────┐
   │ human_        │          │ stop_incident  │
   │ approval()    │          └────────────────┘
   │ ◄─ INTERRUPT  │
   │    Checkpoint │
   │    to SQLite  │
   └────┬──────────┘
        │
(Human resumes via resume.py with approval decision)
        │
   ┌────▼──────────┐
   │execute_action │◄─── MCP tool call
   └────┬──────────┘
        │
   ┌────▼──────────┐
   │   END         │
   │ (RESOLVED)    │
   └───────────────┘
```

**Key Architectural Decisions:**

- **StateGraph + Checkpointing**: Uses LangGraph's state machine abstraction combined with SQLite checkpointing to enable resumable workflows. The entire `IncidentState` is persisted before the `human_approval` interrupt.
- **MCP for Tool Abstraction**: Integrates with external systems (ops, GitHub, Slack) via the Model Context Protocol, allowing tool calls to be routed across subprocess boundaries without tight coupling.
- **Tool-Calling LLM Loop**: The triage subgraph implements an agentic loop where the LLM decides which tools to call, sees results, and decides whether to call more tools or complete analysis.
- **Structured Output**: Forces the LLM to return `Hypothesis` and `RemediationProposal` objects as JSON schema, ensuring downstream code receives valid, typed data.

## Getting Started

### Prerequisites

- **Python 3.11+**
- **venv** (virtual environment manager, comes with Python)
- **npm** (for Slack MCP server, optional if Slack integration not needed)
- **Docker** (for GitHub MCP server, optional if GitHub integration not needed)
- **API Keys**: 
  - Groq API key (free tier available)
  - GitHub PAT (if using GitHub integration)
  - Slack bot token (if using Slack integration)

### Installation

1. **Clone and navigate to the project:**
   ```bash
   cd /path/to/agent_project/backend
   ```

2. **Create and activate a virtual environment:**
   ```bash
   python -m venv venv
   .\venv\Scripts\activate      # Windows
   source venv/bin/activate      # macOS/Linux
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
   
   > **Note**: `requirements.txt` is not yet in the repository. Manually install key packages:
   > ```bash
   > pip install langgraph langchain langchain-groq pydantic python-dotenv
   > pip install groq langsmith httpx aiosqlite
   > pip install mcp fastmcp
   > ```

4. **Set up environment variables:**
   
   Copy the template and fill in your credentials:
   ```bash
   cp .env.example .env
   ```
   
   Edit `.env` with the following variables:

   | Variable | Description | Required | Example |
   |----------|-------------|----------|---------|
   | `GROQ_API_KEY` | API key for Groq LLM inference | Yes | `gsk_...` |
   | `MODEL` | LLM model identifier (Groq-compatible) | No | `openai/gpt-oss-20b` or `mixtral-8x7b-32768` |
   | `LANGSMITH_TRACING` | Enable LangSmith debugging (true/false) | No | `true` |
   | `LANGSMITH_API_KEY` | LangSmith API key (if tracing enabled) | No | `lsv2_pt_...` |
   | `LANGSMITH_ENDPOINT` | LangSmith API endpoint | No | `https://api.smith.langchain.com` |
   | `LANGSMITH_PROJECT` | LangSmith project name | No | `sre_copilot` |
   | `GITHUB_PERSONAL_ACCESS_TOKEN` | GitHub PAT for MCP integration | No | `github_pat_...` |
   | `SLACK_BOT_TOKEN` | Slack bot token for notifications | No | `xoxb-...` |
   | `SLACK_APPROVAL_CHANNEL` | Slack channel for approval requests | No | `#incidents` |
   | `SLACK_MCP_COMMAND` | Command to launch Slack MCP server | No | `npx` |
   | `SLACK_MCP_ARGS` | Arguments for Slack MCP server | No | `-y @slack/mcp-server` |

### Running Locally

**Start an incident investigation (P3 severity, standard workflow):**
```bash
python main.py --scenario checkout --severity P3
```

**Start a P1 incident (urgent, sends immediate Slack notification):**
```bash
python main.py --scenario disk --severity P1
```

**Available scenarios:**
- `checkout` — High error rate on checkout-service due to connection pool exhaustion
- `disk` — payments-worker disk usage critical, unable to write job results

**Expected output:**
- Investigation runs automatically
- Hypothesis is generated (root cause + confidence)
- Remediation action is proposed
- Guardrails validate the action
- If guardrails pass, system pauses for human approval
- CLI displays: `python resume.py <thread_id> approve`

**Resume with approval:**
```bash
python resume.py 1b9cf3fb approve
```

**Resume with denial:**
```bash
python resume.py 1b9cf3fb deny "Safety concern: insufficient testing"
```

## Usage

### Workflow Example: Checkout Service Outage

```bash
# 1. Start investigation
$ python main.py --scenario checkout --severity P3

scenario: checkout   severity: P3   thread_id: 1b9cf3fb
================================================================
INCIDENT REPORT
================================================================
Alert:   High error rate (>20%) on checkout-service for the last 15 minutes.
Status:  PENDING APPROVAL

--- Triage ---
Hypothesis:  Connection pool exhaustion from recent deploy (reduce 20→5)
Confidence:  0.92
Evidence:
  - error_rate_pct: 23.4
  - latency_p99_ms: 4980
  - pool_capacity_pct: 98
  - log: connection pool at 100% capacity

--- Remediation ---
Proposed:   restart_service(checkout-service)
Reasoning:  Restarting will restore pool to default size
Guardrail:  ALLOWED (passed all checks)

--- Timeline ---
1. triage hypothesis: Connection pool exhaustion...
2. proposed: restart_service(checkout-service)
3. guardrail: allowed (passed all checks)
================================================================

Resume with:
  python resume.py 1b9cf3fb approve
  python resume.py 1b9cf3fb deny "reason here"

# 2. Human reviews and approves
$ python resume.py 1b9cf3fb approve

--- Remediation ---
Approval:   APPROVED
Executed:   restart_service(checkout-service) -> ok

--- Timeline ---
...
4. human approval: approved
5. executed restart_service(checkout-service) -> ok
================================================================
```

### Command-Line Arguments

```
python main.py [OPTIONS]

Options:
  --scenario {checkout,disk}  Incident scenario to simulate (default: checkout)
  --severity {P1,P3}         Incident severity level (default: P3)
```

## Project Structure

```
backend/
├── main.py                       # Entry point; CLI argument parsing
├── graph.py                      # LangGraph workflow definition
├── state.py                      # IncidentState TypedDict schema
├── guardrails.py                 # Safety constraint logic
├── models.py                     # Pydantic data models
├── mcp_client.py                 # MCP server integration layer
├── report.py                     # Incident report formatting
├── resume.py                     # Resumption handler for approvals
├── incident.db                   # SQLite checkpoint database (auto-created)
│
├── process/
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── triage.py             # Investigation agent (LLM + tool loop)
│   │   └── remediation.py        # Remediation agent & execution
│   │
│   └── mock_ops/
│       ├── tools.py              # Simulated service operations
│       └── data.py               # Mock logs & metrics
│
├── mcp_server/
│   ├── server.py                 # FastMCP server for ops tools
│   └── __init__.py
│
├── .env                          # Environment variables (secrets)
├── .env.example                  # Template for .env
├── .gitignore
└── venv/                         # Python virtual environment
```

**Key Modules:**

- **main.py**: Parses CLI arguments, initializes the incident graph with SQLite checkpointer, and invokes the workflow.
- **graph.py**: Defines the LangGraph StateGraph; orchestrates triage → proposal → guardrail → approval → execution with conditional routing.
- **process/agents/triage.py**: Builds a subgraph implementing an agentic loop. LLM is bound with three tools (`get_logs`, `get_metrics`, `get_disk_usage`) and uses a `tools_condition` to decide when to call tools vs. summarize.
- **process/agents/remediation.py**: Proposes fixes, manages human approval (via `interrupt()`), and executes MCP tool calls.
- **mcp_client.py**: Abstracts subprocess management for MCP servers; provides `call_mcp_tool(name, args, server)`.
- **guardrails.py**: Implements safety checks (denied actions, allowed services, rate limits).

## Testing

Currently, the system is tested via manual end-to-end scenario runs. No automated test suite is present.

**Manual testing checklist:**

```bash
# Test standard P3 flow
python main.py --scenario checkout --severity P3
python resume.py <thread_id> approve
# Verify: "executed restart_service(checkout-service) -> ok"

# Test P1 flow (checks Slack notification)
python main.py --scenario disk --severity P1
# Verify: P1 notification sent (or warning if Slack unavailable)

# Test guardrail blocking
python main.py --scenario disk --severity P3
# Verify: Guardrail blocks action due to out-of-scope service
# Expected: "Status: BLOCKED (...outside blast radius)"

# Test denial
python main.py --scenario checkout --severity P3
python resume.py <thread_id> deny "Test denial"
# Verify: Status changes to DENIED
```

## Known Limitations & Work in Progress

- **Slack MCP Server Unavailable**: The npm package `@slack/mcp-server` does not exist in the npm registry. Slack notifications fail gracefully (logged warning, workflow continues). To fix: use an alternative Slack integration or implement a custom Slack MCP server.
- **GitHub MCP Requires Docker**: The GitHub MCP server runs in Docker. If Docker is unavailable or GitHub integration is not needed, the `open_revert_pr` action will fail. Implement direct GitHub API calls as an alternative.
- **No API Server**: The system is CLI-only. There is no REST API, HTTP endpoints, or web UI. Suitable for command-line incident response automation; not suitable for integration with incident management platforms without an API layer.
- **Mock Data Only**: The `process/mock_ops/` directory contains simulated logs and metrics. Real integrations would connect to actual services (Prometheus, logs API, Kubernetes, etc.).
- **Single-Shot Scenarios**: The two pre-configured scenarios (`checkout`, `disk`) are hardcoded. Extensibility to custom alerts would require parameterization.
- **No Automatic Execution (by design)**: The system requires explicit human approval before executing any remediation action. This is intentional for safety but means no true "lights-out" automation.
- **Limited Logging**: System uses print statements for output. Production deployment would require structured logging, metrics export, and observability integration.

## Configuration & Customization

### Changing Guardrails

Edit `guardrails.py`:

```python
ALLOWED_SERVICES = {"checkout-service", "payments-worker", "auth-service"}  # Add services
DENIED_ACTIONS = {"drop_database", "delete_resource"}  # Add blocked actions
MAX_ACTIONS_PER_INCIDENT = 5  # Increase rate limit
```

### Adding New Scenarios

Edit `main.py` and add to `ALERTS`:

```python
ALERTS = {
    "checkout": "...",
    "disk": "...",
    "memory_leak": "auth-service memory usage is at 95%"  # Add new
}
```

Then implement corresponding mock data in `process/mock_ops/data.py`.

### Changing the LLM Model

Edit `.env`:

```bash
# Groq models: mixtral-8x7b-32768, llama-3.1-70b, etc.
MODEL=mixtral-8x7b-32768
```

Or use a different provider (e.g., OpenAI via `langchain-openai`):

```python
# In process/agents/triage.py
from langchain_openai import ChatOpenAI
llm = ChatOpenAI(model="gpt-4", temperature=0)
```

## Architecture Decisions & Rationale

**Why LangGraph?**
Provides a declarative, checkpointable state machine for complex multi-step workflows. Enables resumable workflows out-of-the-box with minimal code.

**Why Structured Output (Pydantic)?**
LLMs are probabilistic and sometimes return malformed data. Pydantic validation + LLM schema binding (via `with_structured_output()`) ensures type safety and predictable downstream behavior.

**Why MCP (Model Context Protocol)?**
Decouples tool definitions from tool implementations. MCP servers run in separate processes, allowing integration of diverse systems (GitHub, Slack, custom ops tools) without direct imports or tight coupling. Scalability benefit: tool servers can be load-balanced or auto-scaled independently.

**Why SQLite for Checkpointing?**
Simple, embedded, no external database setup required. Sufficient for single-instance or low-concurrency use cases. For production with high concurrency, upgrade to PostgreSQL via `langgraph_checkpoint_postgres`.

**Why Human Approval (Interrupts)?**
Critical design choice. Autonomous AI executing infrastructure changes is high-risk. Requiring explicit human approval maintains accountability, allows for last-minute vetoes, and provides a feedback loop for the agent to learn from human decisions.

## Contributing

This is a reference implementation for SRE automation using LLM agents. Contributions are welcome. Please:

1. Maintain compatibility with the existing LangGraph + MCP architecture.
2. Add tests for any new scenarios or guardrails.
3. Document new environment variables or configuration options.
4. Ensure human-in-the-loop design principles are preserved.

## License

This project is provided as-is for educational and research purposes. See LICENSE file (if present) for details.

## Future Work

- [ ] REST API for incident triggering and approval management
- [ ] Web dashboard for incident monitoring and approval UI
- [ ] Real service integrations (Prometheus, ELK, Kubernetes API)
- [ ] Multi-agent collaboration (domain-specific specialists)
- [ ] Feedback loop: track which proposals lead to resolution vs. failure
- [ ] Deployment automation: Docker Compose, Helm charts, CloudFormation
- [ ] PostgreSQL checkpointing for production scale
- [ ] OpenTelemetry integration for observability
- [ ] Cost tracking per incident
