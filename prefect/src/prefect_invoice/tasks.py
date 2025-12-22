"""Compatibility layer re-exporting service-specific Prefect tasks.

Each microservice task lives in ``prefect_invoice.services.<service>`` so they
can evolve independently, but importing from ``prefect_invoice.tasks`` keeps
existing call sites working (mirrors the Temporal structure).
"""

from __future__ import annotations

from .services import (
    aggregate_invoice_activity,
    extract_invoice_activity,
    split_pdf_activity,
    upload_pdf_activity,
)

__all__ = [
    "upload_pdf_activity",
    "split_pdf_activity",
    "extract_invoice_activity",
    "aggregate_invoice_activity",
]
