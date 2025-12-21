"""
Orchestration Worker - Temporal worker for invoice orchestration.

This worker registers InvoiceProcessingWorkflow on orchestration-q task queue.
The orchestrator itself has NO activities—it only dispatches to service queues.

Usage:
    uv run python worker.py
"""

import asyncio
import logging
import os
from temporalio.client import Client
from temporalio.contrib.pydantic import pydantic_data_converter
from temporalio.worker import Worker

from invoice_workflow import InvoiceProcessingWorkflow
from shared.config import (
    TASK_QUEUE_ORCHESTRATION,
    TEMPORAL_ADDRESS_LOCAL,
)

TEMPORAL_ADDRESS = os.environ.get("TEMPORAL_ADDRESS", TEMPORAL_ADDRESS_LOCAL)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("orchestration.worker")


async def main():
    """Start Orchestration worker."""
    logger.info(f"Connecting to Temporal server at {TEMPORAL_ADDRESS}...")

    client = await Client.connect(
        TEMPORAL_ADDRESS,
        data_converter=pydantic_data_converter,
    )

    logger.info(f"Starting Orchestration worker on task queue: {TASK_QUEUE_ORCHESTRATION}")
    logger.info("Registered workflows: InvoiceProcessingWorkflow")
    logger.info(
        "NOTE: No activities registered—activities run on service-specific workers"
    )

    worker = Worker(
        client,
        task_queue=TASK_QUEUE_ORCHESTRATION,
        workflows=[InvoiceProcessingWorkflow],
        # NO activities—orchestration only dispatches to other services
    )

    logger.info("Orchestration worker started. Press Ctrl+C to stop.")
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
