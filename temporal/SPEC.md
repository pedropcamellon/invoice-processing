# Temporal Invoice Processing POC - Technical Specifications

## Overview

Temporal implementation of invoice processing orchestration.

| Aspect | Description |
|--------|-------------|
| **Pattern** | Distributed microservices with Temporal task queue routing |
| **Workflow** | Upload → Split → Extract (fan-out) → Aggregate (fan-in) |
| **Communication** | Independent services via Temporal queues (no direct RPC) |
| **Activities** | Mock LLM responses for POC; real integrations for production |
| **State** | Durable history stored in Temporal Server |

## Workflow: InvoiceProcessingWorkflow

**File**: `services/orchestration/invoice_workflow.py`

### Input

```python
InvoiceInput(
    invoice_id: str,
    pdf_filename: str,
    pdf_bytes: bytes  # PDF bytes (base64-encoded)
)
```

### Output

```python
FinalInvoice(
    invoice_id: str,
    vendor: str | None,
    total_amount: float | None,
    invoice_date: str | None,
    confidence_score: float,
    page_count: int
)
```

### Execution Flow

```
Step 1: execute_activity("upload_pdf_activity", ...)
        ↓ [upload-pdf-q] → Upload PDF Service → blob_path
Step 2: execute_activity("split_pdf_activity", ...)
        ↓ [split-pdf-q] → Split PDF Service → page_paths[]
Step 3: execute_activity("extract_invoice_activity", ...) × N pages
        ↓ [extract-invoice-q] → Extract Workers (PARALLEL) → results[]
        ↓ [await asyncio.gather(*tasks)]
Step 4: execute_activity("aggregate_invoice_activity", ...)
        ↓ [aggregate-invoice-q] → Aggregate Service → FinalInvoice
```

## Service Architecture

### Orchestration Service (workflow-q)

**File**: `services/orchestration/`
**Worker**: `services/orchestration/worker.py`
**Client**: `services/orchestration/main.py`

- Registers `InvoiceProcessingWorkflow`
- NO activities (purely orchestration)
- Routes to 4 task queues via activity names

## Project Structure & Dependency Management

This Temporal POC is intentionally multi-service and multi-language friendly. Each worker lives in its own directory under `services/`, owns its dependency graph, and can be implemented in Python, C#, Rust, Go, etc.

### Dependency Management Strategy

#### Python services with `uv`

Each Python worker ships with a minimal `pyproject.toml`:

```toml
[project]
name = "<service-name>"
version = "0.1.0"
description = "<Service description>"
requires-python = ">=3.11,<3.13"
dependencies = [
        "pydantic>=2.11.0",
        "temporalio>=1.20.0",
        # Service-specific deps here
]

[tool.uv]
managed = true
```

Why per-service venv/lockfile?

- Independent deployments (deploy only the worker that changed)
- Smaller Docker images (service-specific deps only)
- No cross-service dependency bleed
- Clear audit trail of what each worker needs

#### Dockerfile pattern (language agnostic)

Every service owns `services/<name>/Dockerfile`. Python workers follow a single-stage pattern: install `uv`, copy `pyproject.toml`, install deps (with fallback), then copy source. `.dockerignore` keeps contexts lean and health checks ensure readiness.

#### Adding new services

1. Create `services/<new-service>/`
2. Add `pyproject.toml` (or equivalent for other languages)
3. Add a Dockerfile following the service template
4. Implement activities/workflows
5. Extend `docker-compose.yml` with the new service definition

### Docker Compose Structure

The root `docker-compose.yml` orchestrates Temporal infra + all workers:

- `docker compose up --build` spins up the full stack
- Compose includes each service file (`include:` directive)
- Shared network `temporal-network` connects every container
- Health checks block worker start until Temporal is healthy

### Build & Deployment

#### Local development (no Docker)

```bash
cd services/upload_pdf
uv sync
uv run python worker.py
```

Repeat per service as needed.

#### Docker development

```bash
# Single worker
docker compose up --build upload-pdf-worker

# Entire stack
docker compose up --build

# Tail logs
docker compose logs -f upload-pdf-worker
```

#### Production deployment

Each worker can be containerized/pushed independently:

```bash
docker build -t myregistry/upload-pdf-service:v1.0 services/upload_pdf
docker push myregistry/upload-pdf-service:v1.0
```

### Best Practices

- One `pyproject.toml`/Dockerfile per service
- Keep shared code minimal (`services/shared/` for Pydantic models/config only)
- Avoid cross-service imports; communicate via Temporal activities
- Use Compose for local orchestration; health checks guard startup
- Maintain `.dockerignore` per service to shrink images

### Troubleshooting

- `failed to compute cache key: '/pyproject.toml' not found` → ensure the file exists within the service directory referenced by the Dockerfile build context.
- `Temporal connection refused` → Temporal server not ready; run `docker compose up postgres temporal` and wait for health checks before starting workers/runner.
- `Module not found` inside containers → missing dependency in the service `pyproject.toml`.

### References

- [Temporal Python SDK](https://temporal.io/docs/dev-guide/python)
- [Temporal Go SDK](https://temporal.io/docs/dev-guide/go)
- [Temporal Java SDK](https://temporal.io/docs/dev-guide/java)
- [uv Package Manager](https://docs.astral.sh/uv/)
- [Docker Build Guide](https://docs.docker.com/build/guide/)

## Deployment & Operations

### Docker Workflow (Recommended)

```powershell
cd temporal

# Infra: Temporal + Postgres + UI
docker compose up postgres temporal temporal-ui

# Workers: orchestration + activities (fan-out/fan-in)
docker compose up --build orchestration-worker upload-pdf-worker split-pdf-worker extract-invoice-worker aggregate-invoice-worker

# Workflow client (runner container)
docker compose run --rm runner

# Tear down stack when finished
docker compose down -v
```

- Runner image caches workflow/client code; rebuild after code edits with `docker compose build runner`.
- Temporal Web UI listens on <http://localhost:8233>; gRPC endpoint is `temporal:7233` inside the Compose network.
- Runner auto-detects Docker (`/.dockerenv`) and defaults to `temporal:7233`; override with `-e TEMPORAL_ADDRESS=...` if needed.

### Local Development

Use only when debugging workers directly:

1. `temporal server start-dev`
2. For each service directory under `services/`, run `uv sync && uv run python worker.py` in separate terminals (orchestration + four activities).
3. Execute workflows via `uv run python main.py` inside `services/orchestration`.

### Observability & Operations

- `docker compose logs -f <service>` for streaming worker logs.
- Scale extract workers to simulate higher throughput: `docker compose up --scale extract-invoice-worker=3`.
- Health checks ensure Temporal services are ready before workers start; if workers exit early, rerun the compose command after the Temporal server reports healthy status.

### Upload PDF Service (upload-pdf-q)

| Aspect | Native Activity Benefit |
|--------|------------------------|
| **Flow Control** | Task Queues provide backpressure—activities only execute when worker has capacity |
| **Heartbeating** | Long-running operations (OCR, diagram extraction) can report progress |
| **Direct Access** | Workers read/write Cosmos DB and Blob Storage without HTTP overhead |
| **Simpler Architecture** | Fewer moving parts (no REST layer between workflow and business logic) |
| **Error Handling** | Exceptions propagate naturally; no HTTP status code translation |
| **Performance** | No network latency between workflow and activity execution |

**External Service Integration:**

For third-party APIs (e.g., Azure Document Intelligence), activities call external services directly via SDK:

### String-Based Invocation

Activities/workflows invoked by **name string**, not Python import:

- Orchestration has zero code dependency on activity implementations
- Each service deploys independently
- Smaller container images (service-specific deps only)

### Per-Service Dockerfiles

Each service has own Dockerfile in `services/<name>/Dockerfile`:

- Smaller images
- Independent build caching
- Clearer service boundaries

### PostgreSQL for Temporal

PostgreSQL in Docker Compose.

## State and Telemetry

**State:** Temporal stores complete execution history on server. Workflow state persists across worker restarts, deployments, and failures.

**Query State:**

```python
# Check status without blocking
description = await workflow_handle.describe()
# description.status -> RUNNING | COMPLETED | FAILED | CANCELED | TERMINATED
# description.raw_description.execution_time -> start time
```

**Telemetry:**

- Temporal Web UI: Full execution history with activity attempts, retries, timings
- Structured logs with planId, correlationId, workflow_id
- OpenTelemetry integration for distributed tracing
- Track activity duration, retry count, end-to-end time via Temporal metrics

**Failure Handling:**

- Transient failures: Retried at activity level per `RetryPolicy`
- Non-transient errors: Workflow fails; exception surfaced via `workflow_handle.result()`
- Manual intervention: Workflows can be cancelled, terminated, or signaled

### Integration Pattern

Workers send telemetry to App Insights via OpenTelemetry:

1. **Traces**: Workflow/activity execution spans
2. **Metrics**: Duration, retry count, queue lag
3. **Logs**: Structured logs with correlation_id

### Setup

Pass `correlation_id` through workflow → activities for end-to-end tracing:

- Workflow logs: `[{correlation_id}] [PdfOcrWorkflow] START`
- Activity logs: `[{correlation_id}] [ocr_page_activity] page=0`
- Query in App Insights: `traces | where message contains "correlation_id"`

### Custom Metrics

Track in activities:

## Microservice Architecture with Temporal

### Service Mesh Pattern

Temporal acts as a service mesh for workflow orchestration across microservices:

```text
┌─────────────────────────────────────────────────────────────┐
│                    Temporal Server                          │
│              (Workflow State + Task Queues)                 │
└─────────────────────────────────────────────────────────────┘
         ↕                    ↕                    ↕
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│  Parse Service  │  │   OCR Service   │  │ Classify Service│
│  Worker + DB    │  │  Worker + DB    │  │  Worker + DB    │
│  parse_activity │  │  ocr_activity   │  │ classify_activity│
└─────────────────┘  └─────────────────┘  └─────────────────┘
         ↑                    ↑                    ↑
┌─────────────────────────────────────────────────────────────┐
│             Parent Workflow (PdfOcrWorkflow)                 │
│  execute_activity(parse) → execute_activity(ocr) → ...       │
└─────────────────────────────────────────────────────────────┘
```

**Key Benefits:**

- **No direct RPC**: Services communicate via Temporal (no REST endpoints between services)
- **Flow control**: Task Queues provide backpressure—activities only execute when worker available
- **Cross-service transactions**: Workflows coordinate multi-service operations with retries/rollbacks
- **Observability**: Full execution history across all services in Temporal Web UI

### Child Workflows for Service Boundaries

For complex multi-service operations, use child workflows to maintain service autonomy:

## Determinism Constraints

Temporal enforces deterministic workflow execution through event sourcing. Workflows must avoid:

- Direct I/O operations (file system, network calls)
- `datetime.now()`, `time.time()`, or random generation (use `workflow.now()` instead)
- Direct calls to external services (use Activities)
- Non-deterministic iteration (dict iteration order)
- Global state mutation

All external calls (blob read/write, Cosmos interactions, Azure Document Intelligence OCR) occur in Activities.

**Determinism Enforcement:**

- Temporal SDK raises `DeterminismError` if workflow behavior changes during replay
- Use `workflow.unsafe.imports_passed_through()` for safe imports of non-deterministic libraries
- Correlation ID passed via workflow input (no dynamic generation after workflow start)

| Don't | Do Instead |
|-------|------------|
| `datetime.now()` | `workflow.now()` |
| `random.random()` | Pass seed via input |
| Direct I/O | Use activities |
| Global state mutation | Local workflow state |

## Retry Policy

All activities use same policy (matches ADF POC):

| Setting | Value |
|---------|-------|
| Initial interval | 5 seconds |
| Max attempts | 3 |
| Backoff coefficient | 2.0 |

## Temporal vs Azure Durable Functions

| Aspect | Temporal | ADF |
|--------|----------|-----|
| Flow control | Task queue backpressure | None |
| Child workflows | Native support | Sub-orchestrations |
| Per-item retry | Activity-level | Manual |
| Observability | Web UI + history | Portal + App Insights |
| Vendor lock-in | OSS, portable | Azure-specific |

## Things to Avoid

| Avoid | Why |
|-------|-----|
| Importing activity code in workflows | Creates monolith |
| Large payloads in activity I/O | Inflates event history |
| SQLite for Temporal | Not supported |
| Single Dockerfile for all services | Larger images, coupled builds |
| Aliases in Pydantic models | Pylance warnings, complexity |

### String-Based Activity Invocation (Cross-Service Independence)

**Critical Concept:** Temporal activities are invoked by **name string**, not Python import. This enables true microservices—the orchestration service has **zero code dependency** on activity implementations.

```python
# ❌ WRONG: Direct import (creates monolith)
from functions.parse_pdf.activities import parse_pdf_activity  # DON'T DO THIS

# ✅ CORRECT: String-based invocation (true microservices)
parse_result = await workflow.execute_activity(
    "parse_pdf_activity",           # Activity name as STRING
    input_data,
    task_queue="parse-service-queue",  # Routes to independent worker
    start_to_close_timeout=timedelta(seconds=60),
)
```

**Why This Matters:**

| Aspect | Import-Based (Monolith) | String-Based (Microservices) |
|--------|-------------------------|------------------------------|
| Orchestration deploys | All activity code bundled | Only workflow definitions |
| Service deploys | N/A (single deployment) | Each service deploys independently |
| Code changes | Redeploy entire application | Redeploy only changed service |
| Python imports | Cross-service imports | No cross-service imports |
| Container size | Large (all dependencies) | Small (service-specific) |

**How It Works:**

1. **Activity worker registers by name:** Each service worker registers its activities with Temporal
2. **Workflow invokes by name string:** `execute_activity("activity_name", ...)` sends task to server
3. **Task queue routing:** Temporal routes task to worker listening on specified `task_queue`
4. **No shared code:** Orchestration service only needs Pydantic models (shared via `mitek-ai-utils` package)

```text
┌─────────────────────────────────────────────────────────────────┐
│                     Temporal Server                             │
│   Receives: execute_activity("parse_pdf_activity", input)       │
│   Routes to: task_queue="parse-service-queue"                   │
└───────────────────────────┬─────────────────────────────────────┘
                            │ Task dispatched
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│           Parse Service Worker (Container App)                  │
│   Registered: activities=[parse_pdf_activity]                   │
│   Listening on: task_queue="parse-service-queue"                │
│   Executes: parse_pdf_activity(input) → returns result          │
└─────────────────────────────────────────────────────────────────┘
```

**Shared Package Pattern (for Pydantic models only):**
**Result:** Orchestration service imports Pydantic models (data contracts), NOT activity code. Each service is independently deployable.
