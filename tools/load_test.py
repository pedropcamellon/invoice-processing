#!/usr/bin/env python3
"""
Load Testing Script for Invoice Processing Workflow

This script submits multiple workflow runs in parallel and incrementally
to test the performance and reliability of the invoice processing workflow.

Usage:
    python load_test.py [options]

Options:
    --base-url      Base URL of the function app (default: http://localhost:8071)
    --pdf-path      Path to a test PDF file (default: uses sample in data folder)
    --total         Total number of workflows to submit (default: 10)
    --batch-size    Number of workflows to submit in each batch (default: 3)
    --delay         Delay between batches in seconds (default: 2)
    --poll-interval Interval to poll for status in seconds (default: 5)
    --timeout       Maximum time to wait for all workflows in seconds (default: 300)
"""

import argparse
import asyncio
import aiohttp
import time
import os
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum


class WorkflowStatus(Enum):
    PENDING = "Pending"
    RUNNING = "Running"
    COMPLETED = "Completed"
    FAILED = "Failed"
    TERMINATED = "Terminated"
    UNKNOWN = "Unknown"


@dataclass
class WorkflowInstance:
    """Tracks a single workflow instance."""

    instance_id: str
    invoice_id: str
    status_url: str
    start_time: float
    end_time: Optional[float] = None
    status: WorkflowStatus = WorkflowStatus.PENDING
    result: Optional[Dict] = None
    error: Optional[str] = None


@dataclass
class LoadTestResults:
    """Aggregated results from load testing."""

    total_submitted: int = 0
    total_completed: int = 0
    total_failed: int = 0
    total_running: int = 0
    start_time: float = 0
    end_time: float = 0
    instances: List[WorkflowInstance] = field(default_factory=list)

    @property
    def duration(self) -> float:
        return self.end_time - self.start_time if self.end_time else 0

    @property
    def success_rate(self) -> float:
        if self.total_submitted == 0:
            return 0
        return (self.total_completed / self.total_submitted) * 100

    @property
    def avg_duration(self) -> float:
        completed = [i for i in self.instances if i.end_time]
        if not completed:
            return 0
        return sum(i.end_time - i.start_time for i in completed) / len(completed)


class LoadTester:
    """Load testing client for the invoice processing workflow."""

    def __init__(
        self,
        base_url: str = "http://localhost:8071",
        pdf_path: Optional[str] = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.pdf_path = pdf_path
        self.results = LoadTestResults()

    async def initialize_storage(self, session: aiohttp.ClientSession) -> bool:
        """Call the startup endpoint to initialize storage containers."""
        try:
            url = f"{self.base_url}/api/startup"
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✓ Storage initialized: {data.get('message', 'OK')}")
                    return True
                else:
                    print(f"✗ Failed to initialize storage: {response.status}")
                    return False
        except Exception as e:
            print(f"✗ Error initializing storage: {e}")
            return False

    async def submit_workflow(
        self,
        session: aiohttp.ClientSession,
        invoice_id: str,
    ) -> Optional[WorkflowInstance]:
        """Submit a single workflow instance."""
        url = f"{self.base_url}/api/invoice/process"

        # Build request body
        body = {
            "invoice_id": invoice_id,
            "metadata": {
                "test_run": True,
                "submitted_at": datetime.utcnow().isoformat(),
            },
        }

        # Add PDF source
        if self.pdf_path and os.path.exists(self.pdf_path):
            body["pdf_path"] = self.pdf_path
        else:
            # Use a default test PDF path
            default_pdf = os.path.join(
                os.path.dirname(os.path.dirname(__file__)), "data", "sample_invoice.pdf"
            )
            if os.path.exists(default_pdf):
                body["pdf_path"] = default_pdf
            else:
                # If no PDF available, the workflow will fail but we can still test submission
                print(f"  Warning: No PDF found, workflow may fail for {invoice_id}")
                body["pdf_path"] = "test.pdf"  # Placeholder

        try:
            start_time = time.time()
            async with session.post(url, json=body) as response:
                if response.status == 202:  # Accepted
                    data = await response.json()
                    instance = WorkflowInstance(
                        instance_id=data.get("id", "unknown"),
                        invoice_id=invoice_id,
                        status_url=data.get("statusQueryGetUri", ""),
                        start_time=start_time,
                    )
                    return instance
                else:
                    text = await response.text()
                    print(
                        f"  ✗ Failed to submit {invoice_id}: {response.status} - {text}"
                    )
                    return None
        except Exception as e:
            print(f"  ✗ Error submitting {invoice_id}: {e}")
            return None

    async def check_status(
        self,
        session: aiohttp.ClientSession,
        instance: WorkflowInstance,
    ) -> WorkflowStatus:
        """Check the status of a workflow instance."""
        if not instance.status_url:
            return WorkflowStatus.UNKNOWN

        try:
            async with session.get(instance.status_url) as response:
                if response.status == 200:
                    data = await response.json()
                    runtime_status = data.get("runtimeStatus", "Unknown")

                    if runtime_status == "Completed":
                        instance.status = WorkflowStatus.COMPLETED
                        instance.end_time = time.time()
                        instance.result = data.get("output")
                    elif runtime_status == "Failed":
                        instance.status = WorkflowStatus.FAILED
                        instance.end_time = time.time()
                        instance.error = data.get("output", "Unknown error")
                    elif runtime_status == "Running":
                        instance.status = WorkflowStatus.RUNNING
                    elif runtime_status == "Pending":
                        instance.status = WorkflowStatus.PENDING
                    elif runtime_status == "Terminated":
                        instance.status = WorkflowStatus.TERMINATED
                        instance.end_time = time.time()
                    else:
                        instance.status = WorkflowStatus.UNKNOWN

                    return instance.status
                else:
                    return WorkflowStatus.UNKNOWN
        except Exception as e:
            print(f"  Warning: Error checking status for {instance.invoice_id}: {e}")
            return WorkflowStatus.UNKNOWN

    async def run_load_test(
        self,
        total: int = 10,
        batch_size: int = 3,
        delay: float = 2.0,
        poll_interval: float = 5.0,
        timeout: float = 300.0,
    ) -> LoadTestResults:
        """
        Run the load test with incremental batch submission.

        Args:
            total: Total number of workflows to submit
            batch_size: Number of workflows per batch
            delay: Delay between batches in seconds
            poll_interval: How often to poll for status
            timeout: Maximum time to wait for completion
        """
        print("\n" + "=" * 60)
        print("Invoice Processing Workflow - Load Test")
        print("=" * 60)
        print(f"Base URL: {self.base_url}")
        print(f"Total workflows: {total}")
        print(f"Batch size: {batch_size}")
        print(f"Delay between batches: {delay}s")
        print(f"Poll interval: {poll_interval}s")
        print(f"Timeout: {timeout}s")
        print("=" * 60 + "\n")

        self.results = LoadTestResults()
        self.results.start_time = time.time()

        async with aiohttp.ClientSession() as session:
            # Initialize storage
            print("Initializing storage...")
            if not await self.initialize_storage(session):
                print("Warning: Storage initialization failed, continuing anyway...")

            # Submit workflows in batches
            print("\nSubmitting workflows...")
            batch_num = 0
            for i in range(0, total, batch_size):
                batch_num += 1
                batch_end = min(i + batch_size, total)
                current_batch_size = batch_end - i

                print(
                    f"\nBatch {batch_num}: Submitting {current_batch_size} workflows..."
                )

                # Submit batch in parallel
                tasks = []
                for j in range(i, batch_end):
                    invoice_id = f"LOAD-TEST-{datetime.now().strftime('%Y%m%d%H%M%S')}-{j + 1:04d}"
                    tasks.append(self.submit_workflow(session, invoice_id))

                instances = await asyncio.gather(*tasks)

                for instance in instances:
                    if instance:
                        self.results.instances.append(instance)
                        self.results.total_submitted += 1
                        print(
                            f"  ✓ Submitted: {instance.invoice_id} (ID: {instance.instance_id[:8]}...)"
                        )

                # Delay before next batch (except for last batch)
                if batch_end < total:
                    print(f"  Waiting {delay}s before next batch...")
                    await asyncio.sleep(delay)

            # Poll for completion
            print(f"\n\nPolling for completion (timeout: {timeout}s)...")
            start_poll = time.time()

            while time.time() - start_poll < timeout:
                # Check status of all pending/running instances
                pending_running = [
                    i
                    for i in self.results.instances
                    if i.status in (WorkflowStatus.PENDING, WorkflowStatus.RUNNING)
                ]

                if not pending_running:
                    break

                # Update status
                for instance in pending_running:
                    await self.check_status(session, instance)

                # Count statuses
                completed = sum(
                    1
                    for i in self.results.instances
                    if i.status == WorkflowStatus.COMPLETED
                )
                failed = sum(
                    1
                    for i in self.results.instances
                    if i.status in (WorkflowStatus.FAILED, WorkflowStatus.TERMINATED)
                )
                running = sum(
                    1
                    for i in self.results.instances
                    if i.status == WorkflowStatus.RUNNING
                )
                pending = sum(
                    1
                    for i in self.results.instances
                    if i.status == WorkflowStatus.PENDING
                )

                elapsed = time.time() - start_poll
                print(
                    f"\r  [{elapsed:.0f}s] Completed: {completed}, Failed: {failed}, Running: {running}, Pending: {pending}   ",
                    end="",
                    flush=True,
                )

                if not pending_running:
                    break

                await asyncio.sleep(poll_interval)

            print()  # New line after polling

        # Calculate final results
        self.results.end_time = time.time()
        self.results.total_completed = sum(
            1 for i in self.results.instances if i.status == WorkflowStatus.COMPLETED
        )
        self.results.total_failed = sum(
            1
            for i in self.results.instances
            if i.status in (WorkflowStatus.FAILED, WorkflowStatus.TERMINATED)
        )
        self.results.total_running = sum(
            1
            for i in self.results.instances
            if i.status in (WorkflowStatus.RUNNING, WorkflowStatus.PENDING)
        )

        return self.results

    def print_results(self) -> None:
        """Print the load test results."""
        print("\n" + "=" * 60)
        print("LOAD TEST RESULTS")
        print("=" * 60)
        print(f"Total Submitted:    {self.results.total_submitted}")
        print(f"Total Completed:    {self.results.total_completed}")
        print(f"Total Failed:       {self.results.total_failed}")
        print(f"Still Running:      {self.results.total_running}")
        print(f"Success Rate:       {self.results.success_rate:.1f}%")
        print(f"Total Duration:     {self.results.duration:.2f}s")
        print(f"Avg Workflow Time:  {self.results.avg_duration:.2f}s")
        print("=" * 60)

        # Print individual results
        if self.results.instances:
            print("\nIndividual Results:")
            print("-" * 60)
            for instance in self.results.instances:
                duration = ""
                if instance.end_time:
                    duration = f" ({instance.end_time - instance.start_time:.2f}s)"
                status_icon = (
                    "✓" if instance.status == WorkflowStatus.COMPLETED else "✗"
                )
                print(
                    f"  {status_icon} {instance.invoice_id}: {instance.status.value}{duration}"
                )
                if instance.error:
                    print(f"      Error: {instance.error}")


async def main():
    parser = argparse.ArgumentParser(
        description="Load testing script for Invoice Processing Workflow"
    )
    parser.add_argument(
        "--base-url",
        default="http://localhost:8071",
        help="Base URL of the function app",
    )
    parser.add_argument("--pdf-path", default=None, help="Path to a test PDF file")
    parser.add_argument(
        "--total", type=int, default=10, help="Total number of workflows to submit"
    )
    parser.add_argument(
        "--batch-size", type=int, default=3, help="Number of workflows per batch"
    )
    parser.add_argument(
        "--delay", type=float, default=2.0, help="Delay between batches in seconds"
    )
    parser.add_argument(
        "--poll-interval",
        type=float,
        default=5.0,
        help="Interval to poll for status in seconds",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=300.0,
        help="Maximum time to wait for all workflows in seconds",
    )

    args = parser.parse_args()

    tester = LoadTester(
        base_url=args.base_url,
        pdf_path=args.pdf_path,
    )

    await tester.run_load_test(
        total=args.total,
        batch_size=args.batch_size,
        delay=args.delay,
        poll_interval=args.poll_interval,
        timeout=args.timeout,
    )

    tester.print_results()


if __name__ == "__main__":
    asyncio.run(main())
