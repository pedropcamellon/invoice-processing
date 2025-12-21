# Extract Invoice Service

Extracts invoice data from page images using mock LLM (for POC).

## Activity

- **Name**: `extract_invoice_activity`
- **Queue**: `extract-invoice-q`
- **Input**: `{invoice_id: str, page_number: int, image_path: str}`
- **Output**: `{invoice_id: str, page_number: int, success: bool, vendor: str | None, amount: float | None, date: str | None, error: str | None}`

## Running Locally

```bash
cd services/extract_invoice
uv sync
uv run python worker.py
```

## Architecture

Part of the distributed invoice processing workflow. Processes page images in parallel via fan-out. Called once per page, then results fan-in to aggregation.
