# Dapr Invoice Workflow

Python-based Dapr Workflow implementation of the invoice processing POC. This implementation demonstrates how the Dapr Workflow building block coordinates multi-application, stateful workloads using deterministic workflows, sidecar service invocation, and workflow management APIs.

## Overview

The workflow orchestrates four independent FastAPI services (upload, split, extract, aggregate) via Dapr service invocation. Each service is fully containerized and can be replaced with implementations in other languages (Go, .NET, Node.js) without changing the workflow logic.

**Key Features:**

- ✅ **Fully Dockerized** - Single command to start entire stack
- ✅ **Clean Architecture** - No path hacks; shared models installed as proper package
- ✅ **Hot-Reload Development** - `docker compose watch` for instant feedback
- ✅ **Visual Monitoring** - Dapr Dashboard at <http://localhost:9999>
- ✅ **Deterministic Workflows** - Reliable replay and state management
- ✅ **Polyglot Ready** - Services can be rewritten in any language

**Tech Stack:**

- Dapr 1.16+ with Workflow building block
- Python 3.11 with `dapr-ext-workflow` SDK
- FastAPI for HTTP services
- Redis for state store (with `actorStateStore` enabled)
- Docker Compose for orchestration
- uv for Python dependency management

## Prerequisites

- **Docker Desktop** (required for all services)
- **Dapr CLI** v1.16+ - [Install Guide](https://docs.dapr.io/getting-started/install-dapr-cli/)
- Optional: Python 3.11+ and [uv](https://docs.astral.sh/uv/) for local development without Docker

## Quick Start

### 1. Start the Stack

```powershell
cd dapr
docker compose up --build
```

This launches:

- **Redis** - State store with health checks
- **Placement** - Required for workflow/actor scheduling  
- **Dashboard** - Web UI at <http://localhost:9999>
- **Workflow App** - Orchestrator at port 8080
- **4 Services** - Upload (7101), Split (7201), Extract (7301), Aggregate (7401)

Wait for all services to show "Application startup complete" in logs.

### 2. Access the Dashboard

Open **<http://localhost:9999>** to view:

- Running Dapr applications
- Component status (Redis state store)
- Service invocation graph
- Application health

### 3. Trigger a Workflow

**Option A: HTTP Request** (via REST Client or Bruno)

```http
POST http://localhost:8080/api/workflows/invoice
Content-Type: application/json

{
  "invoice_id": "INV-2025-001",
  "pdf_path": "sample-invoice.pdf"
}
```

**Option B: Dapr CLI**

```powershell
dapr workflow run invoice_workflow `
  --app-id workflow-app `
  --instance-id INV-2025-001 `
  --input '{"invoice_id": "INV-2025-001", "pdf_path": "sample-invoice.pdf"}'
```

### 4. Check Workflow Status

**HTTP API:**

```powershell
curl http://localhost:8080/api/workflows/INV-2025-001 | ConvertFrom-Json
```

**Dapr CLI:**

```powershell
dapr workflow list --app-id workflow-app
dapr workflow get INV-2025-001 --app-id workflow-app
dapr workflow history INV-2025-001 --app-id workflow-app --output json
```

**Dashboard:**  
View real-time status at <http://localhost:9999>

## Development Workflow

### Hot-Reload with Watch Mode

For development, use watch mode for automatic container updates:

```powershell
docker compose watch
```

This monitors file changes and:

- **Sync + Restart**: Python files (app.py, workflows/) sync and restart the container
- **Rebuild**: Changes to `/shared` package trigger a rebuild

### Viewing Logs

```powershell
# All services
docker compose logs -f

# Specific service
docker compose logs -f workflow-app
docker compose logs -f upload-service

# Filter by time
docker compose logs --since 5m workflow-app
```

### Stopping Services

```powershell
# Stop all
docker compose down

# Stop specific service
docker compose stop workflow-app

# Remove volumes (clears Redis data)
docker compose down -v
```

## Project Structure

```
dapr/
├── docker-compose.yml        # Full stack orchestration with watch mode
├── components/               # Dapr component configs
│   └── statestore.redis.yaml # Redis with actorStateStore enabled
├── shared/                   # Shared Pydantic models (installed as package)
│   ├── models.py
│   └── pyproject.toml
├── workflow_app/
│   ├── Dockerfile            # uv-based build
│   ├── app.py                # FastAPI + workflow runtime
│   └── workflows/
│       └── invoice.py        # Workflow definition + activities
├── services/                 # Independent microservices
│   ├── upload_service/       # Handles PDF upload
│   ├── split_service/        # Splits PDFs into pages
│   ├── extract_service/      # Extracts data per page
│   └── aggregate_service/    # Aggregates results
└── http/
    └── workflow.http         # REST Client test requests
```

## Workflow Execution Flow

1. **Upload Activity** → Copies PDF to `/artifacts/blobs/`
2. **Split Activity** → Generates page metadata (mock)
3. **Extract Activity** → Fan-out extraction per page in parallel
4. **Aggregate Activity** → Combines results into final invoice

Each activity is:

- An independent FastAPI service with its own container
- Called via Dapr service invocation (no direct HTTP)
- Retryable with configurable `RetryPolicy`
- Observable through Dapr Dashboard

## Workflow Management

**Terminate a stuck workflow:**

```http
POST http://localhost:8080/api/workflows/INV-2025-001/terminate
```

**Raise external event:**

```http
POST http://localhost:8080/api/workflows/INV-2025-001/raise-event/approval
Content-Type: application/json

{"approved": true}
```

**Purge completed workflow:**

```powershell
dapr workflow purge INV-2025-001 --app-id workflow-app
```

## Troubleshooting

**Workflow stuck in "Pending":**

- Check Redis is healthy: `docker compose ps redis`
- Verify `actorStateStore: "true"` in components/statestore.redis.yaml
- Restart workflow-app: `docker compose restart workflow-app`

**Service not reachable:**

- Check all sidecars are running: `docker compose ps`
- View sidecar logs: `docker compose logs workflow-app-dapr`
- Verify network: All services should be on `dapr-network`

**Hot-reload not working:**

- Ensure `docker compose watch` is running
- Check file paths in `develop.watch` sections match your edits
- Rebuild manually: `docker compose up --build <service-name>`

## Next Steps

- **See SPEC.md** for implementation details and architectural decisions
- **Production deployment**: See SPEC.md for Kubernetes and cloud deployment patterns
- **Performance testing**: Load test workflows via concurrent HTTP requests
- **Custom activities**: Add new services by copying existing service structure
