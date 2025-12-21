# Upload PDF Service

Handles uploading invoice PDFs to blob storage.

## Activity

- **Name**: `upload_pdf_activity`
- **Queue**: `upload-pdf-q`
- **Input**: `{invoice_id: str, pdf_bytes: bytes}`
- **Output**: `{invoice_id: str, blob_path: str, file_size: int}`

## Running Locally

```bash
cd services/upload_pdf
uv sync
uv run python worker.py
```

## Architecture

Part of the distributed invoice processing workflow. Receives files from the orchestrator and stores them in blob storage (or mock storage for POC).
