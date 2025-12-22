# Prefect Orchestration POC

Prefect-based implementation of the invoice processing workflow. A Prefect Server stack (PostgreSQL + Redis + Prefect server/services/worker) is provided via Docker Compose along with a Python project that defines the `invoice-processing-flow`.

## Quick Start

```powershell
cd prefect

# (One time) create typed work pools for each service
prefect work-pool create --type process upload-pool
prefect work-pool create --type process split-pool
prefect work-pool create --type process extract-pool
prefect work-pool create --type process aggregate-pool

# Point your CLI/profile at the shared Prefect server (so runs show in the UI)
prefect config set PREFECT_API_URL=http://localhost:4200/api

# Start Prefect server stack + service-specific workers
# (each worker container polls its dedicated pool)
docker compose up -d

# Verify the UI
start http://localhost:4200

# Run the workflow locally (no deployment required)
uv sync
uv run prefect-invoice ./data/sample-invoice.pdf --json
```

To scale a specific service, either increase the replica count for the matching
worker container (`docker compose up --scale prefect-worker-extract=3`) or start
additional Prefect workers pointing at the same work pool from other machines.

`prefect-invoice` auto-detects the running server (defaults to
`http://localhost:4200/api`) but you can override it explicitly with
`--api-url http://prefect-server:4200/api` if needed.

See [SPEC.md](SPEC.md) for full architecture, deployment, and scaling details.
