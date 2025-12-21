"""
Invoice Processing Workflow - Temporal workflow for distributed invoice orchestration.

This implements invoice processing using distributed services communicating via Temporal queues:
1. Upload PDF invoice to blob storage
2. Split PDF into page images (fan-out all pages)
3. Extract invoice data from each page (fan-in results)
4. Aggregate results into final invoice

Determinism Requirements:
- No datetime.now(), random(), or I/O operations in workflow body
- All external calls must use execute_activity() or execute_child_workflow()
- Use workflow.now() for timestamps (deterministic during replay)
"""

import asyncio
from datetime import timedelta
from typing import Any

from temporalio import workflow
from temporalio.common import RetryPolicy

from shared.config import (
    TASK_QUEUE_AGGREGATE_INVOICE,
    TASK_QUEUE_EXTRACT_INVOICE,
    TASK_QUEUE_SPLIT_PDF,
    TASK_QUEUE_UPLOAD_PDF,
)

# Define Pydantic models inside unsafe import block to avoid sandbox issues
with workflow.unsafe.imports_passed_through():
    from pydantic import BaseModel, Field

    class InvoiceInput(BaseModel):
        """HTTP request payload for invoice processing."""
        invoice_id: str
        pdf_filename: str
        pdf_bytes: bytes

    class UploadPdfOutput(BaseModel):
        """Output from upload service."""
        invoice_id: str
        blob_path: str
        file_size: int

    class SplitPdfOutput(BaseModel):
        """Output from split service."""
        invoice_id: str
        page_count: int
        page_paths: list[str]

    class ExtractPageInput(BaseModel):
        """Input for extract activity (per page)."""
        invoice_id: str
        page_number: int
        image_path: str

    class ExtractPageOutput(BaseModel):
        """Output from extract activity (per page)."""
        invoice_id: str
        page_number: int
        success: bool
        vendor: str | None = None
        amount: float | None = None
        date: str | None = None
        error: str | None = None

    class AggregateInput(BaseModel):
        """Input for aggregate service."""
        invoice_id: str
        page_results: list[dict[str, Any]]

    class FinalInvoice(BaseModel):
        """Final aggregated invoice result."""
        invoice_id: str
        vendor: str | None = None
        total_amount: float | None = None
        invoice_date: str | None = None
        confidence_score: float
        page_count: int


@workflow.defn
class InvoiceProcessingWorkflow:
    """Orchestrates invoice processing across distributed services."""

    @workflow.run
    async def run(self, invoice_input: InvoiceInput) -> FinalInvoice:
        """Main workflow entrypoint."""
        invoice_id = invoice_input.invoice_id

        # Step 1: Upload PDF
        upload_output = await workflow.execute_activity(
            "upload_pdf_activity",
            {"invoice_id": invoice_id, "pdf_bytes": invoice_input.pdf_bytes},
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=RetryPolicy(maximum_attempts=3),
            task_queue=TASK_QUEUE_UPLOAD_PDF,
        )

        # Step 2: Split PDF into pages
        split_output = await workflow.execute_activity(
            "split_pdf_activity",
            {"invoice_id": invoice_id, "blob_path": upload_output["blob_path"]},
            start_to_close_timeout=timedelta(seconds=60),
            retry_policy=RetryPolicy(maximum_attempts=3),
            task_queue=TASK_QUEUE_SPLIT_PDF,
        )

        # Step 3: Extract invoice data from each page (fan-out)
        extract_tasks = []
        for i, page_path in enumerate(split_output["page_paths"]):
            task = workflow.execute_activity(
                "extract_invoice_activity",
                {"invoice_id": invoice_id, "page_number": i + 1, "image_path": page_path},
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=RetryPolicy(maximum_attempts=2),
                task_queue=TASK_QUEUE_EXTRACT_INVOICE,
            )
            extract_tasks.append(task)

        # Fan-in: Wait for all page extractions
        page_results = await asyncio.gather(*extract_tasks)

        # Step 4: Aggregate all results
        final_invoice = await workflow.execute_activity(
            "aggregate_invoice_activity",
            {"invoice_id": invoice_id, "page_results": page_results},
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=RetryPolicy(maximum_attempts=2),
            task_queue=TASK_QUEUE_AGGREGATE_INVOICE,
        )

        return FinalInvoice(**final_invoice)
