# Workflow Orchestration POC

> **🎓 Evaluation Project**: Comparative analysis of orchestration patterns for distributed workflows. Monorepo containing multiple implementations of the same invoice processing use case using different orchestration frameworks.

## Purpose

This project evaluates and compares orchestration frameworks for implementing distributed workflows. Rather than production code, this repository serves as a decision-making tool and learning resource for understanding the trade-offs between orchestration approaches.

### What You'll Learn

- **Multiple Patterns**: Fan-out/fan-in orchestration across different frameworks
- **Comparative Analysis**: Strengths, weaknesses, and operational characteristics
- **Decision Framework**: How to evaluate orchestration tools for your use case
- **Implementation Patterns**: Real-world examples with the same business logic

## Repository Structure

```
workflow-orchestration-poc/
├── README.md                          # This file - project overview
├── docs/
│   └── comparison-matrix.md           # Side-by-side framework analysis
├── azure-durable-functions/           # ✅ Invoice Processing with Azure Durable Functions
│   ├── README.md                      # ADF-specific setup & architecture
│   ├── SPEC.md                        # Technical specifications
│   ├── function_app.py                # Main orchestrator & HTTP triggers
│   └── ...
└── temporal/                          # ✅ Invoice Processing with Temporal
    ├── README.md                      # Temporal-specific setup
    ├── SPEC.md                        # Technical specifications
    ├── services/
    │   ├── orchestration/             # Workflow orchestrator
    │   ├── upload_pdf/                # Upload service
    │   ├── split_pdf/                 # Split service
    │   ├── extract_invoice/           # Extract service (fan-out)
    │   └── aggregate_invoice/         # Aggregate service (fan-in)
    └── ...
```

## Quick Start

### Azure Durable Functions Implementation

To get started with the Azure Durable Functions implementation:

```powershell
cd azure-durable-functions
uv sync
azurite --silent --location . --debug ./azurite.log   # Terminal 1
uv run func host start -p 8071                         # Terminal 2
curl http://localhost:8071/api/startup                 # Initialize storage
```

See [azure-durable-functions/README.md](azure-durable-functions/README.md) for complete setup instructions.

### Temporal Implementation

*Completed* - See [temporal/README.md](temporal/README.md) for setup instructions.

Implements the same invoice processing workflow using Temporal with distributed microservices communicating via task queues.

## Comparison Framework

### Decision Matrix

| Aspect | Azure Durable Functions | Temporal | [Future: Others] |
|--------|---|---|---|
| **Learning Curve** | Moderate | Moderate | |
| **Setup Complexity** | Easy (Azure emulator) | Moderate (Temporal server) | |
| **Determinism Requirement** | Yes | Yes | |
| **Debugging Experience** | VS Code native | Web dashboard | |
| **Multi-service Decoupling** | HTTP between functions | Task queues (no direct RPC) | |
| **Fan-out/Fan-in** | `context.task_all()` | `asyncio.gather()` | |
| **Production Readiness** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | |
| **Cost (Managed)** | Pay-per-execution | Fixed pricing | |
| **Language Support** | TypeScript, Python | Go, Java, Python, TS | |

For detailed analysis, see [docs/comparison-matrix.md](docs/comparison-matrix.md).

## Use Case: Invoice Processing

All implementations process the same workflow to ensure fair comparison:

```
1. Receive PDF invoice via HTTP
2. Upload to blob storage / external service
3. Split PDF into page images
4. Process all pages IN PARALLEL (LLM extraction - mocked)
5. Aggregate results into structured invoice data
6. Return to client
```

This pattern demonstrates:

- **Fan-out/Fan-in**: Parallel processing at scale
- **Error Handling**: Retry strategies and failure recovery
- **Data Aggregation**: Combining partial results
- **Integration Patterns**: External API coordination

## Prerequisites

- **Python 3.11+**
- **uv** package manager (recommended) or pip
- **Azure Functions Core Tools** v4 (`npm install -g azure-functions-core-tools@4`)
- **Azurite** storage emulator (`npm install -g azurite`) *for ADF implementation*

## Testing & Validation

Each implementation includes:

- **API collections**: Bruno/Postman for manual testing
- **Test scripts**: Verification and load testing tools
- **Sample data**: Example invoices for testing

```powershell
# Load test (from implementation directory)
uv run python tools/load_test.py --pdf-path data/sample-invoice.pdf

# Quick verification
uv run python tools/test_function.py --base-url http://localhost:8071
```

## Contributing

This is a learning/evaluation repository. When adding new patterns:

1. Create a new subdirectory: `pattern-name/`
2. Implement the same invoice processing workflow
3. Update `docs/comparison-matrix.md` with findings
4. Include comprehensive README and SPEC for the pattern

## Next Steps

- [ ] ~~Add Temporal implementation to `temporal/`~~ ✅ **Complete**
- [ ] Expand comparison matrix with additional evaluation criteria
- [ ] Add AWS Step Functions implementation
- [ ] Create architecture decision record (ADR) for framework selection

## License

MIT
