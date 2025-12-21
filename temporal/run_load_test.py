#!/usr/bin/env python
"""
LOADTEST.EXE - Temporal Workflow Load Tester

Submit N workflows with optional delay between submissions.
Supports burst mode (parallel) or ramp mode (staggered).

Usage:
    uv run python run_demo.py                     # 5 workflows, burst mode
    uv run python run_demo.py -n 10               # 10 workflows, burst mode
    uv run python run_demo.py -n 10 -d 500        # 10 workflows, 500ms between each
    uv run python run_demo.py -n 20 -d 100 -p 7234  # custom port

Arguments:
    -n, --count     Number of workflows to submit (default: 5)
    -d, --delay     Delay in ms between submissions, 0=burst (default: 0)
    -p, --port      Temporal server port (default: 7233)
    -h, --help      Show this help
"""

import argparse
import asyncio
import os
import time
import uuid

from temporalio.client import Client
from temporalio.contrib.pydantic import pydantic_data_converter

from shared.workflow import WorkflowInput

# Constants
TASK_QUEUE = "orchestration-q"

# Box drawing chars (DOS style)
TL, TR, BL, BR = "+", "+", "+", "+"
H, V = "-", "|"


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Temporal Workflow Load Tester",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "-n",
        "--count",
        type=int,
        default=int(os.environ.get("WORKFLOW_COUNT", "5")),
        help="Number of workflows to submit (default: 5)",
    )
    parser.add_argument(
        "-d",
        "--delay",
        type=int,
        default=int(os.environ.get("WORKFLOW_DELAY", "0")),
        help="Delay in ms between submissions, 0=burst (default: 0)",
    )
    parser.add_argument(
        "-p",
        "--port",
        type=int,
        default=int(os.environ.get("TEMPORAL_PORT", "7233")),
        help="Temporal server port (default: 7233)",
    )
    parser.add_argument(
        "--host",
        type=str,
        default=os.environ.get("TEMPORAL_HOST", "localhost"),
        help="Temporal server host (default: localhost)",
    )
    return parser.parse_args()


def box(lines: list[str], title: str = "") -> str:
    """Draw a DOS-style box around text."""
    width = max(len(line) for line in lines) + 2
    if title:
        width = max(width, len(title) + 4)

    result = []
    if title:
        result.append(f"{TL}{H * 2} {title} {H * (width - len(title) - 3)}{TR}")
    else:
        result.append(f"{TL}{H * width}{TR}")

    for line in lines:
        result.append(f"{V} {line.ljust(width - 2)} {V}")

    result.append(f"{BL}{H * width}{BR}")
    return "\n".join(result)


def banner() -> str:
    """Return ASCII banner."""
    return r"""
  _    ___   _   ___  _____ ___ ___ _____
 | |  / _ \ /_\ |   \|_   _| __/ __|_   _|
 | |_| (_) / _ \| |) | | | | _|\__ \ | |
 |____\___/_/ \_\___/  |_| |___|___/ |_|
                                    v0.1
"""


async def submit_workflow(client: Client, index: int) -> tuple[str, any]:
    """Submit a single workflow and return (workflow_id, handle)."""
    workflow_id = f"load-{index:02d}-{uuid.uuid4().hex[:6]}"

    workflow_input = WorkflowInput(
        plan_id=f"PLAN-{index:03d}",
        blob_container="demo-container",
        blob_file_path=f"plans/plan_{index}.pdf",
        correlation_id=workflow_id,
    )

    handle = await client.start_workflow(
        "PdfOcrWorkflow",
        workflow_input,
        id=workflow_id,
        task_queue=TASK_QUEUE,
    )

    return workflow_id, handle


async def main():
    """Run load test."""
    args = parse_args()

    temporal_address = f"{args.host}:{args.port}"
    workflow_count = args.count
    delay_ms = args.delay
    mode = "RAMP" if delay_ms > 0 else "BURST"

    print(banner())

    config_lines = [
        f"Workflows:  {workflow_count}",
        f"Mode:       {mode}"
        + (f" ({delay_ms}ms interval)" if delay_ms > 0 else " (parallel)"),
        f"Server:     {temporal_address}",
        f"UI:         http://{args.host}:8080",
    ]
    print(box(config_lines, "CONFIG"))
    print()

    # Connect
    print("[....] Connecting to Temporal server", end="", flush=True)
    try:
        client = await Client.connect(
            temporal_address,
            data_converter=pydantic_data_converter,
        )
        print("\r[ OK ] Connecting to Temporal server")
    except Exception as e:
        print(f"\r[FAIL] Connecting to Temporal server: {e}")
        return 1

    # Submit workflows
    print(f"[....] Submitting {workflow_count} workflows", end="", flush=True)
    submit_start = time.time()

    handles: list[tuple[str, any]] = []

    if delay_ms == 0:
        # Burst mode: submit all in parallel
        tasks = [submit_workflow(client, i + 1) for i in range(workflow_count)]
        handles = await asyncio.gather(*tasks)
    else:
        # Ramp mode: submit with delay between each
        for i in range(workflow_count):
            handle = await submit_workflow(client, i + 1)
            handles.append(handle)
            if i < workflow_count - 1:
                await asyncio.sleep(delay_ms / 1000)

    submit_ms = (time.time() - submit_start) * 1000
    print(f"\r[ OK ] Submitted {workflow_count} workflows in {submit_ms:.0f}ms")

    # Show workflow IDs
    print()
    for wf_id, _ in handles:
        print(f"       > {wf_id}")
    print()

    # Wait for completion
    print(f"[....] Awaiting completion", end="", flush=True)
    exec_start = time.time()

    async def wait_one(wf_id: str, handle) -> dict:
        start = time.time()
        try:
            result = await handle.result()
            return {
                "id": wf_id,
                "ok": True,
                "result": result,
                "ms": (time.time() - start) * 1000,
            }
        except Exception as e:
            return {
                "id": wf_id,
                "ok": False,
                "error": str(e),
                "ms": (time.time() - start) * 1000,
            }

    wait_tasks = [wait_one(wf_id, h) for wf_id, h in handles]
    results = await asyncio.gather(*wait_tasks)

    exec_ms = (time.time() - exec_start) * 1000
    completed = sum(1 for r in results if r["ok"])
    failed = workflow_count - completed

    status = "OK" if failed == 0 else "!!"
    print(f"\r[ {status} ] Awaiting completion ({exec_ms:.0f}ms)")
    print()

    # Results table
    print("  ID                  TIME     PAGES  OCR   STATUS")
    print("  " + "-" * 52)

    for r in sorted(results, key=lambda x: x["ms"]):
        wf_id = r["id"]
        ms = r["ms"]
        if r["ok"]:
            res = r["result"]
            pages = res.get("parse", {}).get("page_count", "?")
            ocr_ok = res.get("ocr", {}).get("successful_pages", "?")
            print(f"  {wf_id}  {ms:6.0f}ms  {pages:>5}  {ocr_ok:>3}   [OK]")
        else:
            err = r.get("error", "unknown")[:20]
            print(f"  {wf_id}  {ms:6.0f}ms  {'--':>5}  {'--':>3}   [FAIL] {err}")

    # Summary
    print()
    avg_ms = sum(r["ms"] for r in results) / len(results) if results else 0
    throughput = workflow_count / (exec_ms / 1000) if exec_ms > 0 else 0

    summary_lines = [
        f"Completed:   {completed}/{workflow_count}",
        f"Failed:      {failed}",
        f"Wall-clock:  {exec_ms:.0f}ms",
        f"Avg/wf:      {avg_ms:.0f}ms",
        f"Throughput:  {throughput:.1f} wf/sec",
    ]
    print(box(summary_lines, "RESULTS"))
    print()

    if failed == 0:
        print("<<< ALL WORKFLOWS COMPLETED SUCCESSFULLY >>>")
    else:
        print(f"<<< WARNING: {failed} WORKFLOW(S) FAILED >>>")
    print()

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    import sys

    sys.exit(asyncio.run(main()))
