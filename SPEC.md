# Technical Specification

## Overview

Invoice processing system built with Azure Durable Functions demonstrating the **Fan-out/Fan-in** orchestration pattern. Receives PDF invoices, splits into pages, processes in parallel with LLM extraction (mocked), and aggregates results.

---

## Architecture

### Blueprint Pattern

This project uses Azure Functions Python v2 **Blueprint Pattern** - the recommended approach for modular, testable codebases.

| File | Responsibility |
|------|---------------|
| `function_app.py` | Main app entry point, HTTP triggers, orchestrators |
| `activities/__init__.py` | Exports `activity_blueprints` list for registration |
| `activities/upload_pdf.py` | PDF upload to blob storage |
| `activities/split_pdf.py` | PDF to page images (PyMuPDF @ 144 DPI) |
| `activities/extract_invoice.py` | LLM extraction (mocked, ready for GPT-4 Vision) |
| `activities/aggregate_invoice.py` | Combines page results into final invoice |
| `storage_helper.py` | Azurite/Azure Blob Storage operations |
| `tools/test_function.py` | Endpoint verification script |
| `tools/load_test.py` | Parallel workflow load testing |

**Key Principle**: Blueprints are created in separate files and registered with the main app. This avoids circular dependencies and enables independent testing.

---

## Workflow

### Invoice Processing Pipeline

```
HTTP POST /api/invoice/process
    ↓
[1] Upload PDF → pdfs/{invoice_id}.pdf
    ↓
[2] Split PDF → images/{invoice_id}/page_{n}.png (PyMuPDF @ 144 DPI)
    ↓
[3] Fan-out: Extract data from each page in parallel (LLM mock: 2-5s each)
    ↓
[4] Fan-in: Aggregate all page results into final invoice structure
    ↓
Return structured invoice JSON
```

### Storage Layout

| Container | Purpose | Example Path |
|-----------|---------|--------------|
| `pdfs/` | Original PDF documents | `pdfs/INV-2025-001.pdf` |
| `images/` | Extracted page images | `images/INV-2025-001/page_0.png` |

---

## Components

### HTTP Triggers

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/invoice/process` | POST | Start invoice processing. Accepts `pdf_path`, `pdf_url`, or `pdf_base64` |
| `/api/startup` | GET | Initialize blob storage containers |

### Orchestrators

**`invoice_orchestrator`**: Coordinates the 4-step workflow using Fan-out/Fan-in pattern. Deterministic, stateless, and resilient to failures. State managed by Durable Functions runtime in Azure Storage.

### Activity Functions

| Activity | Input | Output | Notes |
|----------|-------|--------|-------|
| `upload_pdf_to_storage_activity` | PDF path/URL/base64 | Blob URL | Creates containers if needed |
| `split_pdf_to_images` | Blob URL, invoice_id | List of page metadata | Real implementation using PyMuPDF |
| `extract_invoice_data_from_page` | Page metadata | Extracted data | **Mocked** - ready for GPT-4 Vision |
| `aggregate_invoice_data` | All page results | Final invoice structure | Combines header, line items, summary |

### Extraction Logic (Mocked)

| Page Position | Data Extracted |
|--------------|----------------|
| First page | Header: invoice number, dates, vendor/customer info |
| Middle pages | Line items: description, quantity, price, amount |
| Last page | Summary: totals, payment terms |

---

## Configuration

### Required Environment Variables

| Variable | Purpose | Local Value |
|----------|---------|-------------|
| `AzureWebJobsStorage` | Durable Functions state (queues/tables) | `UseDevelopmentStorage=true` |
| `AZURE_STORAGE_CONNECTION_STRING` | Blob storage for PDFs/images | Azurite connection string |
| `FUNCTIONS_WORKER_RUNTIME` | Runtime identifier | `python` |

### Azurite Services

| Service | Port | Purpose |
|---------|------|---------|
| Blob | 10000 | PDF and image storage |
| Queue | 10001 | Durable Functions task queues |
| Table | 10002 | Orchestration history |

---

## Design Decisions

### Why Blueprint Pattern?
- **Modularity**: Each domain has its own blueprint
- **No Circular Dependencies**: Blueprints don't import the main app
- **Testability**: Blueprints can be tested independently
- **Scalability**: Easy to add more blueprints as project grows

### Why Fan-out/Fan-in?
- **Parallelism**: Process N pages in time of 1 page (plus overhead)
- **Resilience**: Failed pages can be retried independently
- **Scalability**: Azure Functions handles concurrent execution

### Why Azurite?
- **Local Development**: Full Azure Storage emulation
- **No Cloud Costs**: Develop and test locally
- **Identical API**: Same code works with real Azure Storage

---

## Scaling Guidelines

| File Size | Recommendation |
|-----------|----------------|
| < 300 lines | Keep together |
| 300-600 lines | Consider splitting |
| > 600 lines | Split into blueprints |

### Current Structure (Implemented)

```
function_app.py           # HTTP triggers + orchestrator
activities/
  ├── __init__.py         # Exports activity_blueprints list
  ├── upload_pdf.py       # upload_pdf_to_storage_activity
  ├── split_pdf.py        # split_pdf_to_images
  ├── extract_invoice.py  # extract_invoice_data_from_page
  └── aggregate_invoice.py # aggregate_invoice_data
storage_helper.py         # Blob storage utilities
tools/
  ├── test_function.py    # Endpoint verification
  └── load_test.py        # Parallel load testing
```

---

## Naming Conventions

| Type | Convention | Example |
|------|------------|---------|
| Blueprints | `*_bp` | `activities_bp`, `pdf_bp` |
| Activities | `*_activity` | `upload_pdf_activity` |
| Orchestrators | `*_orchestrator` | `invoice_orchestrator` |
| HTTP triggers | Action-based | `process_invoice`, `startup` |

---

## Error Handling

Activities should return structured responses:

```python
{"status": "success", "data": result}
{"status": "error", "error": "Description"}
```

Orchestrators rely on Durable Functions' built-in retry mechanisms and state persistence for resilience.

---

## Future Roadmap

### Phase 1: Current ✅
- Blueprint pattern implementation (modular activities)
- Azurite integration
- Fan-out/Fan-in workflow
- Mocked LLM extraction
- Development tools (test_function.py, load_test.py)
- Load tested: 100% success rate, ~9s avg per workflow

### Phase 2: Production Ready
- Real GPT-4 Vision integration
- Comprehensive error handling
- Retry policies
- Unit and integration tests

### Phase 3: Cloud Deployment
- Azure deployment configuration
- CI/CD pipeline
- Application Insights
- Key Vault for secrets
- Managed Identity

### Phase 4: Advanced Features
- Database storage (CosmosDB)
- Webhook notifications
- Batch processing
- Multi-language invoice support
