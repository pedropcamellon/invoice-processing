"""
Extract Invoice Worker - Temporal worker for invoice extraction service.

This worker registers extract_invoice_activity on the extract-invoice-q task queue.

Usage:
    uv run python worker.py
"""

import asyncio
import logging
import os

from temporalio.client import Client
from temporalio.contrib.pydantic import pydantic_data_converter
from temporalio.worker import Worker

from activities import extract_invoice_activity
from shared.config import TASK_QUEUE_EXTRACT_INVOICE, TEMPORAL_ADDRESS_LOCAL

TEMPORAL_ADDRESS = os.environ.get("TEMPORAL_ADDRESS", TEMPORAL_ADDRESS_LOCAL)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("extract-invoice.worker")


async def main():
    """Start Extract Invoice worker."""
    logger.info(f"Connecting to Temporal server at {TEMPORAL_ADDRESS}...")

    client = await Client.connect(
        TEMPORAL_ADDRESS,
        data_converter=pydantic_data_converter,
    )

    logger.info(f"Starting Extract Invoice worker on task queue: {TASK_QUEUE_EXTRACT_INVOICE}")
    logger.info("Registered activities: extract_invoice_activity")

    worker = Worker(
        client,
        task_queue=TASK_QUEUE_EXTRACT_INVOICE,
        activities=[extract_invoice_activity],
    )

    logger.info("Extract Invoice worker started. Press Ctrl+C to stop.")
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
