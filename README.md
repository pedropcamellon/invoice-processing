# Workflow Orchestration POC

Comparative analysis of orchestration patterns for distributed workflows. Monorepo containing multiple implementations of the same invoice processing use case using different orchestration frameworks.

## Purpose

This project evaluates and compares orchestration frameworks for implementing distributed workflows. Rather than production code, this repository serves as a decision-making tool and learning resource for understanding the trade-offs between orchestration approaches.

### What You'll Learn

- **Multiple Patterns**: Fan-out/fan-in orchestration across different frameworks
- **Comparative Analysis**: Strengths, weaknesses, and operational characteristics
- **Decision Framework**: How to evaluate orchestration tools for your use case
- **Implementation Patterns**: Real-world examples with the same business logic

## Repository Structure

This monorepo contains four complete implementations of the same invoice processing workflow, each in its own directory:

**`azure-durable-functions/`** - Azure Durable Functions implementation with Azurite local storage. Includes `function_app.py` orchestrator, activity functions, and HTTP triggers. See implementation-specific README and SPEC for architecture details.

**`temporal/`** - Temporal workflow with distributed microservices. Each service (upload, split, extract, aggregate) runs independently and communicates via Temporal task queues. The `services/orchestration/` directory contains the workflow definition.

**`prefect/`** - Prefect 3 implementation with self-hosted server (PostgreSQL + Redis). Flow and task definitions live in `src/prefect_invoice/`. Includes docker-compose stack for the Prefect server components.

**`dapr/`** - Dapr Workflow building block implementation. Combines a Python workflow orchestrator (`workflow_app/`) with independent activity services behind Dapr sidecars. Each service is polyglot-ready and can be swapped to any language without changing the workflow code.

**`docs/`** - Contains `comparison-matrix.md` with detailed side-by-side analysis of all frameworks.

Each implementation directory contains its own README (quick start), SPEC (technical details), and supporting files (docker-compose, API collections, test scripts).

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

See [temporal/README.md](temporal/README.md) for setup instructions.

Implements the same invoice processing workflow using Temporal with distributed microservices communicating via task queues.

**Note**: Temporal's Go and Java SDKs are most mature for production use. Python and TypeScript SDKs are well-supported but consider Java/Go for critical production workflows.

### Prefect Implementation

See [prefect/README.md](prefect/README.md) for instructions.

Demonstrates the invoice workflow using Prefect 3 with a self-hosted server (PostgreSQL + Redis) and Prefect flow/tasks representing the services.

**Note**: Prefect is Python-only, making it ideal for Python-native teams and data engineering workflows. No polyglot support.

### Dapr Workflow Implementation

See [dapr/README.md](dapr/README.md) for setup instructions.

Runs the workflow using the Dapr Workflow building block (Python orchestrator + independent services). Each activity service runs behind its own Dapr sidecar, enabling future language swaps without touching the workflow code.

**Note**: Dapr has a strong .NET/C# community with mature tooling. Python support for workflows is developing but less mature than C# implementations. Consider C# for production Dapr workflows.

## Comparison Framework

### Decision Matrix

| Aspect | Azure Durable Functions | Temporal | Prefect | Dapr Workflow |
|--------|------------------------|----------|---------|---------------|
| **Language Support** | C#, TypeScript, Python, Java | Java, TypeScript, Python, Go | **Python only** | Any language (strong .NET/C# community, developing Python support) |
| **Primary Ecosystem** | .NET & Azure-first | Polyglot (Java/Go production-grade) | Python data/ML workflows | .NET/C# (Python experimental for workflows) |
| **Learning Curve** | Moderate | Moderate | Low (Python-native) | Moderate (Dapr concepts + CLI) |
| **Setup Complexity** | Easy (Azurite) | Moderate (Temporal server) | Easy (Docker Compose) | Moderate (Redis + placement + sidecars) |
| **Determinism Requirement** | Yes | Yes | No (dynamic) | Yes (workflow replay) |
| **Debugging Experience** | VS Code native | Temporal Web UI | Prefect UI | Dapr CLI + Dashboard |
| **Multi-service Decoupling** | HTTP between functions | Task queues (no direct RPC) | Direct Python calls | Service invocation across isolated apps |
| **Fan-out/Fan-in** | `context.task_all()` | `asyncio.gather()` | Native Python patterns | Child workflows + parallel activities |
| **Cost (Managed)** | Pay-per-execution | Fixed pricing | Cloud or self-hosted | Portable (self-host or AKS/EKS) |
| **Best For** | Azure-native apps | Critical workflows, polyglot | Data pipelines, ML workflows | Microservices, multi-language distributed systems |

For detailed analysis, see [docs/comparison-matrix.md](docs/comparison-matrix.md).

## Use Case: Invoice Processing

All implementations process the same workflow to ensure fair comparison:

1. Receive PDF invoice via HTTP
2. Upload to blob storage / external service
3. Split PDF into page images
4. Process all pages IN PARALLEL (LLM extraction - mocked)
5. Aggregate results into structured invoice data
6. Return to client

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
- **Dapr CLI** v1.16+ and Docker (for Redis + placement) *for Dapr implementation*

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

## License

MIT
