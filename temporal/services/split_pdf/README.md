# Split PDF Service

Splits invoice PDFs into individual page images.

## Activity

- **Name**: `split_pdf_activity`
- **Queue**: `split-pdf-q`
- **Input**: `{invoice_id: str, blob_path: str}`
- **Output**: `{invoice_id: str, page_count: int, page_paths: list[str]}`

## Running Locally

```bash
cd services/split_pdf
uv sync
uv run python worker.py
```

## Architecture

Part of the distributed invoice processing workflow. Receives uploaded PDF path from orchestrator and splits it into page images for parallel processing.
