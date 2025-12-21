# Temporal Orchestration POC

Invoice-processing workflow implemented on Temporal to demonstrate fan-out/fan-in orchestration across independent services. For full architecture, workflow diagrams, and implementation notes see [temporal/SPEC.md](temporal/SPEC.md).

## Prerequisites

- Docker Desktop with Compose v2
- ~6 GB free RAM for Temporal + workers
- Optional (local fallback): Python 3.11 and [uv](https://docs.astral.sh/uv/)

## Quick Start

```powershell
cd temporal

# 1. Infra (Temporal + Postgres + UI)
docker compose up postgres temporal temporal-ui

# 2. Workers (orchestration + 4 activities)
docker compose up --build orchestration-worker upload-pdf-worker split-pdf-worker extract-invoice-worker aggregate-invoice-worker

# 3. Trigger workflow client (runner container)
docker compose run --rm runner

# 4. Tear down when finished
docker compose down -v
```

Notes:

- Rebuild the runner after editing workflow/client code: `docker compose build runner`.
- Temporal Web UI is available at <http://localhost:8233>.
- For manual, non-Docker workflows (e.g., debugging with uv), follow the instructions in [temporal/SPEC.md](temporal/SPEC.md#local-development) instead of the commands above.
