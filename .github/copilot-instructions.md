# Copilot Instructions for Invoice Processing Workflow

## Project Overview

Azure Durable Functions (Python v2) implementing **Fan-out/Fan-in** pattern for invoice processing. PDFs are uploaded, split into page images, processed in parallel, and aggregated.

## Architecture

### Core Components

- **`function_app.py`** - HTTP triggers (`/api/invoice/process`, `/api/startup`) + orchestrator (`invoice_orchestrator`)
- **`activities/`** - Modular activity blueprints (one per file):
  - `upload_pdf.py` → `upload_pdf_to_storage_activity`
  - `split_pdf.py` → `split_pdf_to_images` (uses PyMuPDF)
  - `extract_invoice.py` → `extract_invoice_data_from_page` (mocked LLM)
  - `aggregate_invoice.py` → `aggregate_invoice_data`
- **`storage_helper.py`** - Azurite blob storage utilities (upload, download, URL generation)

### Blueprint Pattern

Activities use `df.Blueprint()` and are registered in `function_app.py`:

```python
# activities/__init__.py exports activity_blueprints list
from activities import activity_blueprints
for bp in activity_blueprints:
    myApp.register_functions(bp)
```

### Data Flow

```
HTTP POST → orchestrator → upload_pdf → split_pdf → [extract_invoice × N pages] → aggregate → response
```

## Development Workflow

### Prerequisites

```powershell
# Terminal 1: Start Azurite storage emulator
azurite --silent --location . --debug ./azurite.log

# Terminal 2: Start function app (port 8071 to avoid conflicts)
uv run func host start -p 8071

# Initialize storage containers (required once)
curl http://localhost:8071/api/startup
```

### Using uv

This project uses **uv** as the package manager. Always prefix Python commands with `uv run`:

```powershell
# Run any Python script
uv run python <script.py>

# Install/sync dependencies
uv sync

# Add a new dependency
uv add <package-name>
```

### Testing

- **Bruno collections**: `bruno/invoice_processing/` for manual API testing
- **Load testing**: `uv run python tools/load_test.py --pdf-path data/sample-invoice.pdf`
- **Quick verification**: `uv run python tools/test_function.py --base-url http://localhost:8071`

### Sample PDF

Use `data/sample-invoice.pdf` for testing workflows.

## Code Conventions

### Activity Functions

- Decorator: `@blueprint.activity_trigger(input_name="payload")`
- Input/output: Always `Dict[str, Any]` (JSON-serializable)
- Logging prefix: `[ACTIVITY:NAME]` (e.g., `[ACTIVITY:UPLOAD_PDF]`)
- Always ensure containers exist before blob operations

### Orchestrator Rules (Durable Functions)

- **Must be deterministic** - no random, datetime.now(), or I/O
- Use `yield context.call_activity()` for activity calls
- Fan-out: `tasks = [context.call_activity(...) for item in items]`
- Fan-in: `results = yield context.task_all(tasks)`

### Storage

- Azurite connection string in `local.settings.json`
- Containers: `pdfs` (uploaded PDFs), `images` (page images)
- Blob naming: `{invoice_id}.pdf`, `{pdf_id}/page_{n}.png`

## Key Files Reference

| File | Purpose |
|------|---------|
| `function_app.py` | Entry point, HTTP triggers, orchestrator |
| `activities/__init__.py` | Exports all blueprints for registration |
| `storage_helper.py` | Blob storage CRUD operations |
| `local.settings.json` | Azurite connection, runtime config |
| `pyproject.toml` | Dependencies (azure-functions-durable, pymupdf) |

## Common Issues

- **Port 7071 busy**: Use `-p 8071` when starting func host
- **Connection errors**: Ensure Azurite is running first
- **"No job functions found"**: Run `uv sync` to install dependencies
