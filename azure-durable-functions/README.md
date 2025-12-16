# Azure Durable Functions - Invoice Processing

> **Part of [workflow-orchestration-poc](../README.md) monorepo** - Comparative analysis of orchestration patterns. See [comparison matrix](../docs/comparison-matrix.md) for ADF vs alternatives.

> **🎓 Implementation Reference**: This directory implements the invoice processing workflow using Azure Durable Functions to demonstrate the fan-out/fan-in pattern.

## Overview

A Python-based Azure Durable Functions application demonstrating the **Fan-out/Fan-in** orchestration pattern through a practical invoice processing example.

### What You'll Learn

- **Durable Functions Concepts**: Orchestrators, activities, and the replay pattern
- **Blueprint Pattern**: Microsoft's recommended approach for organizing Azure Functions
- **Fan-out/Fan-in**: Parallel processing with result aggregation
- **Local Development**: Using Azurite storage emulator
- **Real-world Workflow**: PDF splitting, parallel processing, data aggregation

### How It Works

1. Receive PDF invoice via HTTP
2. Upload to blob storage and split into page images
3. Process all pages **in parallel** (LLM extraction - mocked)
4. Aggregate results into structured invoice data

> 📖 See [SPEC.md](SPEC.md) for detailed technical specifications and architecture decisions.

## Prerequisites

- **Python 3.11+**
- **Azure Functions Core Tools** v4 (`npm install -g azure-functions-core-tools@4`)
- **Azurite** storage emulator (`npm install -g azurite`)
- **uv** package manager (recommended) or pip

## Quick Start

### 1. Install Dependencies

```powershell
uv sync          # or: pip install -r requirements.txt
```

### 2. Start Azurite (Terminal 1)

```powershell
azurite --silent --location . --debug ./azurite.log
```

### 3. Start Function App (Terminal 2)

```powershell
uv run func host start -p 8071
```

### 4. Initialize Storage

```powershell
curl http://localhost:8071/api/startup
```

### 5. Process an Invoice

```powershell
curl -X POST http://localhost:8071/api/invoice/process `
  -H "Content-Type: application/json" `
  -d '{"invoice_id": "INV-2025-001", "pdf_path": "data/sample-invoice.pdf"}'
```

The response includes a `statusQueryGetUri` to check processing status.

## Project Structure

```
├── function_app.py      # HTTP triggers + orchestrators
├── activities/          # Modular activity blueprints
│   ├── __init__.py      # Exports activity_blueprints list
│   ├── upload_pdf.py    # PDF upload to blob storage
│   ├── split_pdf.py     # PDF to images (PyMuPDF)
│   ├── extract_invoice.py # LLM extraction (mocked)
│   └── aggregate_invoice.py # Results aggregation
├── storage_helper.py    # Blob storage utilities
├── tools/               # Development utilities
│   ├── test_function.py # Endpoint verification
│   └── load_test.py     # Parallel workflow testing
├── bruno/               # API testing collections
└── data/                # Sample files (sample-invoice.pdf)
```

## Key Concepts Demonstrated

### 1. The Replay Pattern

Orchestrators **replay from the beginning** after each activity completes. History is stored in Azure Storage, and completed activities return instantly from history. This is why orchestrator code must be **deterministic**.

### 2. Fan-out/Fan-in

Process multiple items in parallel, then aggregate:

```python
# Fan-out: Create parallel tasks
tasks = [context.call_activity("extract_page", page) for page in pages]

# Fan-in: Wait for all
results = yield context.task_all(tasks)
```

### 3. Blueprint Pattern

Organize code into modular blueprints that are registered with the main app:

```python
# activities.py
activities_bp = df.Blueprint()

@activities_bp.activity_trigger(input_name="payload")
def my_activity(payload): ...

# function_app.py
myApp.register_functions(activities_bp)
```

## Testing

### Quick Verification

```powershell
uv run python tools/test_function.py --base-url http://localhost:8071 --pdf-path data/sample-invoice.pdf
```

### Load Testing

```powershell
uv run python tools/load_test.py --pdf-path data/sample-invoice.pdf --total 10 --batch-size 3
```

### Manual API Testing

Bruno API collections are included in `bruno/invoice_processing/` for endpoint testing.

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "No job functions found" | Run `uv sync` and verify Python 3.11+ |
| Connection errors | Ensure Azurite is running before starting function app |
| Orchestration stuck | Check Azurite logs at `./azurite.log` |

## Learn More

- [Azure Durable Functions Documentation](https://learn.microsoft.com/azure/azure-functions/durable/)
- [Durable Functions Patterns](https://learn.microsoft.com/azure/azure-functions/durable/durable-functions-overview)
- [Blueprint Pattern Documentation](https://learn.microsoft.com/azure/azure-functions/functions-reference-python#blueprints)

## License

MIT
