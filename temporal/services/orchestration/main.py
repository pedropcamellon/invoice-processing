"""
Orchestration Client - Starts and monitors invoice processing workflows.

This client connects to Temporal and starts invoice_processing_workflow instances,
then polls for progress and displays results.

Usage:
    uv run python main.py
    docker compose run --rm runner
"""

import asyncio
import json
import logging
import os
from datetime import datetime
from pathlib import Path

from temporalio.client import Client
from temporalio.contrib.pydantic import pydantic_data_converter

from invoice_workflow import FinalInvoice, InvoiceInput
from shared.config import (
    TASK_QUEUE_ORCHESTRATION,
    TEMPORAL_ADDRESS_DOCKER,
    TEMPORAL_ADDRESS_LOCAL,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("orchestration.client")


def _running_inside_docker() -> bool:
    """Detect Docker by probing /.dockerenv."""
    return Path("/.dockerenv").exists()


TEMPORAL_ADDRESS = os.environ.get(
    "TEMPORAL_ADDRESS",
    TEMPORAL_ADDRESS_DOCKER if _running_inside_docker() else TEMPORAL_ADDRESS_LOCAL,
)
WORKFLOW_ID = "invoice-processing"


async def main():
    """Start an invoice processing workflow and monitor progress."""
    logger.info(f"Connecting to Temporal server at {TEMPORAL_ADDRESS}...")

    try:
        client = await Client.connect(
            TEMPORAL_ADDRESS,
            data_converter=pydantic_data_converter,
        )
        logger.info("Connected to Temporal")
    except Exception as e:
        logger.error(f"Failed to connect: {e}")
        return

    # Mock invoice data for testing
    mock_pdf = b"%PDF-1.4\nMock invoice PDF data"

    invoice_input = InvoiceInput(
        invoice_id="INV-20241221-001",
        pdf_filename="invoice.pdf",
        pdf_bytes=mock_pdf,
    )

    logger.info(f"Starting workflow: {WORKFLOW_ID}")
    logger.info(f"Invoice: {invoice_input.invoice_id}")

    try:
        handle = await client.start_workflow(
            "InvoiceProcessingWorkflow",
            invoice_input,
            id=WORKFLOW_ID,
            task_queue=TASK_QUEUE_ORCHESTRATION,
        )
        logger.info(f"Workflow started with ID: {handle.id}")
    except Exception as e:
        logger.error(f"Failed to start workflow: {e}")
        return

    # Wait for workflow to complete
    logger.info("Waiting for workflow to complete...")
    start_time = datetime.now()

    try:
        result = await handle.result()
        final_invoice = FinalInvoice.model_validate(result)

        elapsed = (datetime.now() - start_time).total_seconds()
        logger.info("Workflow completed!")
        logger.info(f"Processing time: {elapsed:.1f}s")

        # Display results
        logger.info("=" * 70)
        logger.info("WORKFLOW RESULT")
        logger.info("=" * 70)
        logger.info(json.dumps(final_invoice.model_dump(), indent=2))
        logger.info("=" * 70)

    except Exception as e:
        logger.error(f"Workflow failed: {e}")
        return


if __name__ == "__main__":
    asyncio.run(main())
