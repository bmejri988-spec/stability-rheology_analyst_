# Stability Rheology Analyst

AI-powered assistant for cosmetic formulation analysis focused on rheology behavior, physical stability risk, and environmental safety support.

The project combines:
- A tool-using LLM agent for formulation assessment
- A Django backend exposing API endpoints
- A React + Vite frontend for interactive usage
- An MCP server for tool-style integration and local testing
- An evaluation workspace for quality and release scoring

## Core Capabilities

- Stability and rheology assessment from structured formula input
- Tool-augmented reasoning (RAG, ingredient lookup, PubChem, RDKit, literature search, experimental data bridges)
- Safety/environment follow-up analysis using a dedicated safety flow
- Conversational rheology assistant endpoint for chat-style usage
- Local MCP tools for integration tests and workflow automation

## Tech Stack

- Python 3.11-3.12
- Django 5
- LangChain + Azure OpenAI
- Qdrant vector search
- React 18 + TypeScript + Vite + Tailwind

## Repository Structure

- `agent/`: agent construction, prompts, and fallback chat logic
- `backend/`: Django app and MCP server
- `frontend/`: React client
- `tools/`: domain tools (RAG, chemistry, literature, web, experimental)
- `models/`: pydantic schemas and agent response models
- `rag/`: ingestion and vector store utilities
- `evaluation/`: benchmark data, scoring scripts, and reports
- `data/`: formulation and experimental reference data

## Prerequisites

- Python 3.11 or 3.12
- Node.js 18+ (Node 20 LTS recommended)
- npm

## Environment Variables

Create a `.env` file in the repository root with at least:

```dotenv
# Azure OpenAI
AZURE_OPENAI_API_KEY=
AZURE_OPENAI_ENDPOINT=
CHAT_DEPLOYMENT_NAME=
EMBEDDING_DEPLOYMENT_NAME=

# Qdrant
QDRANT_URL=
QDRANT_API_KEY=
QDRANT_COLLECTION=rheology_docs

# Optional integrations
SERPAPI_API_KEY=
SEMANTIC_SCHOLAR_URL=
SEMANTIC_SCHOLAR_API_KEY=
FIRECRAWL_URL=https://api.firecrawl.dev/v2/agent
FIRECRAWL_API_KEY=

# Runtime behavior
ASSESSMENT_ENFORCE_TOOL_COVERAGE_RETRY=false
```

Note: some legacy keys are still accepted by the code (for backward compatibility), but uppercase names are preferred.

## Quick Start

### 1) Backend / Agent Environment

From repository root:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e .
```

Run Django API:

```bash
python backend/manage.py runserver
```

Backend base URL: `http://127.0.0.1:8000`

### 2) Frontend

```bash
cd frontend
npm install
npm run dev
```

Optional API override:

```bash
export VITE_API_BASE_URL=http://127.0.0.1:8000
```

### 3) CLI Formula Assessment (Optional)

```bash
python main.py
```

Paste a JSON payload matching the formulation schema and submit an empty line to run.

## API Endpoints

All routes are served under `/api`.

- `GET /api/health` -> service health check
- `POST /api/assess-formula` -> stability/rheology assessment
- `POST /api/assess-safety` -> environmental/safety follow-up based on report + formula
- `POST /api/agent2-chat` -> conversational rheology assistant

## MCP Server

Run MCP server locally:

```bash
python backend/mcpServer.py
```

Exposed MCP tools include:
- `health`
- `stability_rheology_check`
- `safety_environment`
- `rheology_assistant`

You can use the provided scripts (for example `mcp_client_test.py`) to validate MCP behavior.

## Evaluation

The `evaluation/` workspace provides dry-run and live scoring flows.

From project root:

```bash
python evaluation/scripts/run_agent_eval.py --mode dry-run
python evaluation/scripts/run_llm_eval.py --mode dry-run
python evaluation/scripts/run_project_eval.py
```

For live runs, start backend first and pass base URL where required.

## Sample Input

Use `stability_sample.json` and `models/formula_schema.py` as references for valid payload shape and constraints.

## Security Notes

- Do not commit real API keys or tokens.
- Rotate any credential that was ever exposed in logs, screenshots, or shared snippets.
- Keep production secrets in secure secret managers where possible.

## License

Add your license here (for example: MIT).

