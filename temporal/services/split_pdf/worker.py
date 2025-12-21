"""
Split PDF Worker - Temporal worker for PDF split service.

This worker registers split_pdf_activity on the split-pdf-q task queue.

Usage:
    uv run python worker.py
"""

import asyncio
import logging
import os

from temporalio.client import Client
from temporalio.contrib.pydantic import pydantic_data_converter
from temporalio.worker import Worker

from activities import split_pdf_activity
from shared.config import TASK_QUEUE_SPLIT_PDF, TEMPORAL_ADDRESS_LOCAL

TEMPORAL_ADDRESS = os.environ.get("TEMPORAL_ADDRESS", TEMPORAL_ADDRESS_LOCAL)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("split-pdf.worker")


async def main():
    """Start Split PDF worker."""
    logger.info(f"Connecting to Temporal server at {TEMPORAL_ADDRESS}...")

    client = await Client.connect(
        TEMPORAL_ADDRESS,
        data_converter=pydantic_data_converter,
    )

    logger.info(f"Starting Split PDF worker on task queue: {TASK_QUEUE_SPLIT_PDF}")
    logger.info("Registered activities: split_pdf_activity")

    worker = Worker(
        client,
        task_queue=TASK_QUEUE_SPLIT_PDF,
        activities=[split_pdf_activity],
    )

    logger.info("Split PDF worker started. Press Ctrl+C to stop.")
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
