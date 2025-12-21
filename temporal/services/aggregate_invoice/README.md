# Aggregate Invoice Service

Aggregates extracted invoice data from all pages into final result.

## Activity

- **Name**: `aggregate_invoice_activity`
- **Queue**: `aggregate-invoice-q`
- **Input**: `{invoice_id: str, page_results: list[dict]}`
- **Output**: `{invoice_id: str, vendor: str | None, total_amount: float | None, invoice_date: str | None, confidence_score: float, page_count: int}`

## Running Locally

```bash
cd services/aggregate_invoice
uv sync
uv run python worker.py
```

## Architecture

Part of the distributed invoice processing workflow. Fan-in point that combines results from parallel extract operations and produces the final invoice.
