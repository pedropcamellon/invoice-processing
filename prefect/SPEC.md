# Prefect Invoice Processing POC - Technical Specification

## Overview

Prefect-based replica of the invoice processing workflow (upload → split → extract → aggregate) used across this repository. The implementation demonstrates how Prefect 3 orchestrates fan-out/fan-in pipelines while remaining infrastructure-agnostic.

| Aspect | Description |
| --- | --- |
| Orchestrator | Prefect 3 (flow + task decorators)
| Services | Pure Prefect tasks (mock implementations for blob/OCR)
| State Storage | Prefect Server backed by PostgreSQL and Redis
| Deployment | Docker Compose (server, services, worker) + Python project for flow code

## Code Layout

```
prefect/
├── README.md            # Quick start
├── SPEC.md              # This document
├── docker-compose.yml   # Prefect server stack
├── pyproject.toml       # uv-managed project definition
└── src/prefect_invoice/
   ├── __init__.py
   ├── cli.py           # Simple CLI to run the flow
   ├── flow.py          # Prefect flow definition
   ├── models.py        # Pydantic models shared by tasks
   ├── tasks.py         # Re-exports for backwards compatibility
   └── services/        # Upload/Split/Extract/Aggregate task modules
```

## Workflow: `invoice_processing_flow`

1. `upload_pdf_activity` – stores the PDF (mock storage) and returns a blob path
2. `split_pdf_activity` – splits PDF into individual page images
3. `extract_invoice_activity` – runs per-page extraction (fan-out via mapped tasks)
4. `aggregate_invoice_activity` – aggregates the page results into a final invoice summary

Prefect handles the fan-out/fan-in lifecycle and persists results in PostgreSQL via the server stack.

## Docker Compose Stack

A self-hosted Prefect server (database + Redis + server/services/workers) is provided in [docker-compose.yml](docker-compose.yml). The relevant services are:

- `postgres`: state backend
- `redis`: messaging broker/cache
- `prefect-server`: Prefect API/UI (`http://localhost:4200`)
- `prefect-services`: background services (scheduling, automations)
- `prefect-worker-<service>`: four independent workers, each polling a dedicated work pool (`upload-pool`, `split-pool`, `extract-pool`, `aggregate-pool`)

> **One-time setup:** create the pools before bringing up the stack
>
> ```powershell
> prefect work-pool create --type process upload-pool
> prefect work-pool create --type process split-pool
> prefect work-pool create --type process extract-pool
> prefect work-pool create --type process aggregate-pool
> ```

### Running the stack

```powershell
cd prefect
docker compose up -d
# wait for health checks (~1 minute)
open http://localhost:4200
```

Shut down with `docker compose down` (use `-v` to reset Postgres/Redis data).

## Running the Prefect Flow Locally

1. Install dependencies with uv:

   ```powershell
   cd prefect
   uv sync
   ```

2. Point the CLI at the running server so runs land in the UI:

   ```powershell
   prefect config set PREFECT_API_URL=http://localhost:4200/api
   ```

   (You can also pass `--api-url` to `prefect-invoice`; if the setting is missing,
   the CLI attempts to auto-detect `http://localhost:4200/api`.)

3. Execute the flow:

   ```powershell
   uv run prefect-invoice ../data/sample-invoice.pdf --json
   ```

   Provide any PDF file path; the tasks mock external services so the file is not parsed.

The CLI bypasses deployment registration by running the flow in-process, which is ideal for local iteration. To leverage the server stack’s orchestration features, you can register and run deployments using `prefect deployment build` / `prefect deployment run` commands targeting the `invoice_processing_flow`.

### Scaling Workers / Multi-container Execution

- The `docker-compose.yml` file starts one worker container per logical service so you can independently scale them with `docker compose up --scale prefect-worker-extract=3`, etc.
- Alternatively, start additional workers manually: `prefect worker start --pool extract-pool` (after configuring `PREFECT_API_URL`).
- Use Prefect deployments plus work pools to run different stages on specific infrastructure; each pool encapsulates its infrastructure template.

## Local Development Notes

- Tasks are defined in `prefect_invoice.tasks`, making them easy to test individually.
- Shared Pydantic models define contracts between tasks, mirroring the Temporal project structure.
- The CLI uses Prefect’s synchronous execution for simplicity; switch to asynchronous execution or Prefect deployments for production usage.

## Observability

- Prefect UI (<http://localhost:4200>) shows flow runs, task statuses, retries.
- Use `docker compose logs -f` to aggregate server/worker logs, or tail individual containers, e.g., `docker compose logs -f prefect-worker`.

## Troubleshooting

| Issue | Resolution |
| --- | --- |
| UI not available on port 4200 | Ensure no other service uses the port; confirm containers are healthy with `docker compose ps` |
| Worker not connecting | Verify `prefect-worker` has `PREFECT_API_URL` pointing to `http://prefect-server:4200/api` (set in compose file) |
| Flow cannot import package | Run `uv sync` again or ensure PYTHONPATH includes `src/` when executing directly |
| PostgreSQL errors | `docker compose down -v` to reset volumes if needed |

## Next Steps

- Replace mock task implementations with real storage/OCR integrations.
- Add Prefect deployments + automation policies for scheduled processing.
- Integrate Prefect Cloud credentials for managed execution if desired.
