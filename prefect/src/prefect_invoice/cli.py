"""Command-line helper to trigger the Prefect invoice workflow locally."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

from .flow import invoice_processing_flow
from .models import InvoiceInput

DEFAULT_API_URL = "http://localhost:4200/api"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the Prefect invoice workflow locally",
    )
    parser.add_argument("pdf", type=Path, help="Path to PDF file to process")
    parser.add_argument(
        "--invoice-id",
        default="INV-PREFECT-001",
        help="Stable invoice identifier",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print workflow result as JSON",
    )
    parser.add_argument(
        "--api-url",
        help=(
            "Prefect API to send runs to. Defaults to auto-detecting "
            "http://localhost:4200/api if reachable; otherwise a temporary "
            "local server is used."
        ),
    )
    return parser.parse_args()


def ensure_prefect_api(api_url: str | None) -> None:
    """Wire the CLI to the long-running Prefect server when available."""

    if api_url:
        os.environ["PREFECT_API_URL"] = api_url
        return

    if os.environ.get("PREFECT_API_URL"):
        return

    try:
        urlopen(f"{DEFAULT_API_URL}/health", timeout=2)
    except URLError:
        return
    except Exception:
        return

    os.environ["PREFECT_API_URL"] = DEFAULT_API_URL


def main() -> None:
    args = parse_args()
    ensure_prefect_api(args.api_url)
    pdf_bytes = args.pdf.read_bytes()

    invoice = InvoiceInput(
        invoice_id=args.invoice_id,
        pdf_filename=args.pdf.name,
        pdf_bytes=pdf_bytes,
    )

    final_invoice = invoice_processing_flow(invoice)

    if args.json:
        print(json.dumps(final_invoice.model_dump(), indent=2))
    else:
        print(f"Workflow completed for {final_invoice.invoice_id}")
        print(f"Vendor: {final_invoice.vendor}")
        print(f"Total amount: {final_invoice.total_amount}")


if __name__ == "__main__":  # pragma: no cover - CLI entrypoint
    main()
