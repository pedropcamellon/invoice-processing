# Orchestration Service

Temporal workflow orchestrator for the invoice processing pipeline.

## Pipeline

```
InvoiceProcessingWorkflow
├── upload_pdf_activity (store PDF in blob storage)
├── split_pdf_activity (split into pages)
├── parallel: extract_invoice_activity × N pages (fan-out)
└── aggregate_invoice_activity (combine results - fan-in)
```

**Key Pattern:** Orchestration service coordinates workflow but has NO activities. All activities execute on service-specific task queues (upload-pdf-q, split-pdf-q, extract-invoice-q, aggregate-invoice-q).

## Usage

```bash
# Docker (Recommended) - starts orchestration worker
docker compose up orchestration-worker

# Docker - run workflow client (runner container)
docker compose run --rm runner

# Docker - rebuild runner after workflow changes
docker compose build runner

# Local - start worker (fallback)
uv run python worker.py

# Local - run workflow (fallback)
uv run python main.py
```

## Environment

- `TEMPORAL_ADDRESS` - Temporal server (default: `localhost:7233`)
