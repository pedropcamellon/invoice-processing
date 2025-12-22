# Dapr Invoice Processing POC - Technical Specification

## Overview

Dapr-based replica of the invoice processing workflow (upload → split → extract → aggregate). This implementation demonstrates how the Dapr Workflow building block coordinates multi-application, stateful workloads using deterministic workflows, sidecar building blocks, and workflow management APIs.

| Aspect | Description |
| --- | --- |
| Orchestrator | Dapr Workflow runtime (Python `dapr-ext-workflow` SDK)
| Activities | Dedicated microservices (Python, Go, .NET, Node.js, etc.) exposed via Dapr service invocation APIs
| State Store | Redis (local dev) via Dapr state management component
| Messaging | Dapr pub/sub for optional notifications (future)
| Deployment | `dapr` apps launched via `dapr run` or Docker Compose (placement + Redis + services)

## Objectives

1. Mirror existing invoice workflow to allow apples-to-apples comparison with Prefect, Temporal, and ADF.
2. Showcase Dapr Workflow capabilities: deterministic orchestration, child workflows, durable timers, workflow CLI (pause/resume/terminate/purge).
3. Demonstrate multi-application, polyglot orchestration where each activity runs inside its own Dapr-enabled app (potentially written in different languages) while the workflow remains Python-based.
4. Provide guidance for scaling, managing, and updating Dapr workflows safely (determinism + replay constraints).

## Directory Layout

```
dapr/
├── README.md                 # Quick start + Docker Compose instructions
├── SPEC.md                   # This document
├── docker-compose.yml        # Full stack: Redis + placement + dashboard + all services
├── components/               # Dapr component yamls (state store, pub/sub)
│   └── statestore.redis.yaml # Redis with actorStateStore enabled
├── shared/                   # Shared Pydantic models as installable package
│   ├── __init__.py
│   ├── models.py
│   └── pyproject.toml
├── workflow_app/
│   ├── Dockerfile            # Multi-stage build with uv + shared package
│   ├── app.py                # FastAPI host + workflow runtime registration
│   ├── pyproject.toml        # uv project for orchestration service
│   └── workflows/
│       └── invoice.py        # `invoice_workflow` + child workflow + activities
├── services/                 # Independent microservices, each Dockerized
│   ├── upload_service/
│   │   ├── Dockerfile
│   │   ├── app.py
│   │   └── pyproject.toml
│   ├── split_service/
│   │   ├── Dockerfile
│   │   ├── app.py
│   │   └── pyproject.toml
│   ├── extract_service/
│   │   ├── Dockerfile
│   │   ├── app.py
│   │   └── pyproject.toml
│   └── aggregate_service/
│       ├── Dockerfile
│       ├── app.py
│       └── pyproject.toml
├── http/
│   └── workflow.http         # REST Client / Bruno requests for testing
├── scripts/
│   ├── start-local.ps1       # Launch via `dapr run` for dev (optional)
│   └── seed-data.ps1         # Copy sample PDFs
└── _artifacts/               # Runtime-generated blobs/images (Docker volume)
```

## Workflow Definition (`invoice_workflow`)

1. **Input**: `InvoiceRequest(invoice_id: str, pdf_path: str | None, pdf_url: str | None)`
2. **Activities**:
   - `upload_pdf_activity` (app-id: `upload-service`)
   - `split_pdf_activity` (app-id: `split-service`)
   - `extract_invoice_activity` (app-id: `extract-service`, invoked per page)
   - `aggregate_invoice_activity` (app-id: `aggregate-service`)
3. **Flow**:
   - Run upload → split sequentially.
   - Fan out extraction via `context.call_activity` per page using `Task.all` semantics.
   - Optional child workflow (`page_batch_workflow`) groups pages in batches of N for demonstration.
   - Aggregate page summaries into final invoice payload.
4. **Determinism considerations**:
   - Use `context.current_utc_datetime()` for timestamps.
   - Avoid randomness; if needed, call helper activities for ID generation.
   - Store any configuration via workflow input or Dapr state lookups inside activities.
5. **Retry policy**: `RetryPolicy(max_number_of_attempts=3, first_retry_interval=timedelta(seconds=1))` applied to all activity calls.

### Child Workflow: `page_batch_workflow`

When more than two pages exist, the parent workflow spawns `page_batch_workflow` children, each processing a batch of two pages via the same extraction activity and returning their results. This keeps the parent history small (matching the replay requirements highlighted in the Dapr sample) and demonstrates multi-application workflows because each child still calls the standalone extract service.

## Runtime Components

| Component | Purpose |
| --- | --- |
| Dapr Placement Service | Required for workflow + actor scheduling (runs in Docker via compose).
| Redis | Serves as Dapr state store with `actorStateStore: true` for workflow/actor support.
| Dapr Dashboard | Web UI at `http://localhost:9999` for visualizing apps, components, and invocations.
| Workflow App (`workflow-app`) | Hosts REST endpoint to start workflows and contains workflow definition.
| Activity Apps | Four independent FastAPI services with Dapr sidecars; each fully Dockerized with uv-based dependency management.
| Docker Compose | Orchestrates entire stack with hot-reload via `watch` mode for development.
| Shared Package | `/shared` directory installed into all containers during build; no path hacks or sys.path manipulation.

### Service Contracts

| Service | App ID | Endpoint | Request | Response |
| --- | --- | --- | --- | --- |
| Upload | `upload-service` | `POST /upload` | `InvoiceRequest` | `UploadResult` (copies PDFs to `/artifacts/blobs/`) |
| Split | `split-service` | `POST /split` | `UploadResult` | `SplitResult` (writes placeholder PNG metadata) |
| Extract | `extract-service` | `POST /extract` | `PageMetadata` | `PageExtraction` (deterministic mock values) |
| Aggregate | `aggregate-service` | `POST /aggregate` | `{ invoice_id, pages: list[PageExtraction] }` | `AggregatedInvoice` |

## Local Development Plan

ocker Desktop (required for Redis, placement, and all services)

- Dapr CLI v1.16+ (for workflow management commands)
- Optional: Python 3.11 + `uv` if running services locally without Docker

2. **Start entire stack**

   ```powershell
   cd dapr
   docker compose up --build
   ```

   This launches:
   - Redis with health checks
   - Placement service
   - Dapr Dashboard (<http://localhost:9999>)
   - Workflow app + sidecar (port 8080)
   - Four activity services + sidecars (ports 7101, 7201, 7301, 7401)

3. **Development with hot-reload**

   ```powershell
   docker compose watch
   ```

   - Syncs Python file changes and restarts containers automatically
   - Rebuilds on shared package modifications

4. **Trigger workflow**

   Via HTTP:

   ```http
   POST http://localhost:8080/api/workflows/invoice
   Content-Type: application/json

   {
     "invoice_id": "INV-2025-001",
     "pdf_path": "sample-invoice.pdf"
   }
   ```

   Or via Dapr CLI:

   ```powershell
   dapr workflow run invoice_workflow --app-id workflow-app --instance-id INV-2025-001 \
     --input '{"invoice_id": "INV-2025-001", "pdf_path": "sample-invoice.pdf"}'
   ```

5. **Monitor workflows**
   - Web UI: <http://localhost:9999>
   - HTTP API: `GET http://localhost:8080/api/workflows/INV-2025-001`
   - CLI: `dapr workflow list --app-id workflow-app`

## Container Architecture

Each service uses a clean, dependency-injection approach.

**Key decisions:**

- **No sys.path hacks**: Shared package installed cleanly via `uv pip install`
- **Environment-driven paths**: Services use `ARTIFACT_DIR` and `SOURCE_BASE_DIR` env vars
- **Deterministic builds**: `pyproject.toml` pins dependencies; uv ensures reproducible installs
- **Volume mounts**: Data from monorepo root (`../data`), artifacts on Docker volumer workflow list --app-id workflow-app --filter-status RUNNING
   dapr workflow history INV-service has its own `Dockerfile` using uv for dependency management. Shared package copied and installed during build - no runtime path manipulation.
- **Docker Compose**: Production-ready compose file with:
  - Health checks for Redis
  - Proper service dependencies (`condition: service_healthy`)
  - Named volumes for artifacts persistence
  - Network isolation via `dapr-network`
  - Watch mode for development hot-reload
- **Kubernetes**: Use Dapr Helm chart for control plane, define `dapr.io/app-id` annotations per Deployment. Workflow runtime runs inside orchestrator deployment.
- **State Store Configuration**: Redis requires `actorStateStore: "true"` metadata for workflow support. Production deployments should use Azure Cosmos DB, AWS DynamoDB, or PostgreSQL.
- **Secrets**: Integrate Dapr Secrets component (Azure Key Vault, AWS Secrets Manager) for API keys used by activities.
- **Versioning**: When updating workflow logic, create new workflow names (e.g., `invoice_workflow_v2`) to avoid determinism issues for in-flight instances.

## Observability

- **Dapr Dashboard**: Visual UI for app status, components, and service graph at <http://localhost:9999>
- **Logging**: Aggregate via `docker compose logs -f` or individual service logs
- **Tracing**: Enable OpenTelemetry exporters in Dapr configuration for distributed tracing
- **Metrics**: Dapr sidecars expose Prometheus metrics on port 9090
- **Workflow State**: Query via HTTP API or CLI commands for instance status and history

- **Start / trigger**: `dapr workflow run` CLI or `POST /api/workflows/invoice` (wraps `start_workflow` exactly like the upstream SDK example).
- **Status / history**: `GET /api/workflows/{id}` mirrors `dapr workflow get`; CLI history/list commands remain available.
- **Lifecycle controls**: HTTP endpoints expose raise-event & terminate flows; CLI still supports pause/resume/terminate/purge because we rely on the stock `dapr` workflow component backed by Redis.
- **External events**: `POST /api/workflows/{id}/raise-event/{event}` forwards to `raise_workflow_event`, matching the behavior shown in the reference snippet.

## Reference Sample & Workflow Capabilities

The official Dapr Python SDK example (excerpt included in the user request) showcases everything we plan to leverage:

- `WorkflowRuntime` hosts workflows/activities in-process for local dev; in our project this lives inside `workflows/app.py`.
- `RetryPolicy` objects attached to `ctx.call_activity` / `ctx.call_child_workflow` provide durable retries identical to the sample’s `hello_retryable_act` and `child_retryable_wf` flow.
- Child workflows (`ctx.call_child_workflow`) and durable timers (`ctx.wait_for_external_event`, `ctx.sleep`) allow us to partition page batches or wait for approvals, mirroring the `child_wf` + external event raised via CLI in the snippet.
- Management operations (`start_workflow`, `pause_workflow`, `resume_workflow`, `terminate_workflow`, `raise_workflow_event`, `purge_workflow`) are accessible through the Dapr CLI/HTTP APIs, meaning we can script lifecycle tests exactly as the reference sample does once our workflow app is running under `dapr run`.

This confirms the desired behavior—Python orchestrator plus independently deployed services with retries, child workflows, and event handling—is fully supported by Dapr Workflow.

## Scaling Strategy

- **Integration tests**: Launch minimal stack via Docker Compose in CI, verifying end-to-end JSON output matches Prefect/Temporal results.
- **Load testing**: Fire multiple workflow starts concurrently via HTTP API and observe throughput.
- **Manual testing**:
  - REST Client / Bruno collection in `/http/workflow.http`
  - Dapr Dashboard for visual workflow inspection
  - CLI commands for workflow management (`dapr workflow list/get/terminate`)
- **Hot-reload development**: `docker compose watch` provides instant feedback on code changesternal workflows.
- **Resiliency**: Configure workflow-level retry policies (max attempts, backoff coefficient) plus Dapr resiliency policies in `resiliency.yaml` for network retries.
- **State store considerations**: Redis works for dev; production should use Cosmos DB, DynamoDB, or SQL (verify compatibility with workflow history requirements).

## Observability

- Enable Dapr tracing via `dapr run --enable-api-logging --enable-app-health-checks`.
- Collect logs through Docker Compose aggregated logging or `dapr logs --app-id <id>`.
- Add OpenTelemetry exporters (Jaeger/Zipkin) for workflow + activity spans.
- Provide a Grafana dashboard referencing Dapr metrics (sidecar exposes Prometheus endpoint on `:9090`).

## Testing & Tooling

- **Unit tests**: Exercise workflow determinism using the Python SDK’s `WorkflowRuntime` test harness.
- **Integration tests**: Launch minimal stack via `pytest` + `dapr run` wrappers, verifying end-to-end JSON output matches Prefect/Temporal results.
- **Load testing**: `tests/load_test.py` fire multiple `dapr workflow run` commands concurrently and observe queue depth + throughput.
- **Manual**: Bruno collection hitting `http://localhost:3500/v1.0/workflows/workflow-app/invoice_workflow/start` and management endpoints.

## Deployment Considerations

- **Containerization**: Each app includes its own `Dockerfile` installing deps via `uv`. Compose or Kubernetes manifests orchestrate multiple apps + placement service.
- **Kubernetes**: Use Dapr Helm chart for control plane, define `dapr.io/app-id` annotations per Deployment. Workflow runtime runs inside orchestrator deployment.
- **Secrets**: Integrate Dapr Secrets component (Azure Key Vault, AWS Secrets Manager) for API keys used by activities.
- **Versioning**: When updating workflow logic, create new workflow names (e.g., `invoice_workflow_v2`) to avoid determinism issues for in-flight instances.
