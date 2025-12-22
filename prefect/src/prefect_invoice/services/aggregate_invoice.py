"""Aggregate invoice service task."""

from __future__ import annotations

from prefect import task

from ..models import ExtractResult, FinalInvoice


@task(name="aggregate_invoice_activity")
def aggregate_invoice_activity(invoice_id: str, page_results: list[ExtractResult]) -> FinalInvoice:
    """Combine per-page extraction into a final invoice summary."""

    total_amount = sum(result.amount or 0 for result in page_results)
    vendor = next((result.vendor for result in page_results if result.vendor), None)

    return FinalInvoice(
        invoice_id=invoice_id,
        vendor=vendor,
        total_amount=round(total_amount, 2) or None,
        invoice_date="2025-12-01",
        confidence_score=0.87,
        page_count=len(page_results),
        page_results=[result.model_dump() for result in page_results],
    )
