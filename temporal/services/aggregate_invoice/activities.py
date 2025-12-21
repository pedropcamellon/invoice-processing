"""
Aggregate Invoice Service - Aggregates extracted invoice data from all pages.

Activity: aggregate_invoice_activity
Task Queue: aggregate-invoice-q
"""

from typing import Any
from temporalio import activity


@activity.defn
async def aggregate_invoice_activity(payload: dict[str, Any]) -> dict[str, Any]:
    """
    Aggregate extracted invoice data from all pages.
    
    Input:
        - invoice_id: str
        - page_results: list[dict] (results from extract_invoice_activity)
    
    Returns:
        - invoice_id: str
        - vendor: str | None
        - total_amount: float | None
        - invoice_date: str | None
        - confidence_score: float
        - page_count: int
    """
    invoice_id = payload.get("invoice_id")
    page_results = payload.get("page_results", [])
    
    # Simple aggregation: take first non-null values
    vendor = None
    total_amount = 0.0
    invoice_date = None
    
    for result in page_results:
        if vendor is None and result.get("vendor"):
            vendor = result.get("vendor")
        if invoice_date is None and result.get("date"):
            invoice_date = result.get("date")
        if result.get("amount"):
            total_amount += result.get("amount", 0)
    
    # Mock confidence score (average of successful extractions)
    successful = sum(1 for r in page_results if r.get("success"))
    confidence_score = (successful / len(page_results)) if page_results else 0.0
    
    print(
        f"[AGGREGATE_INVOICE] {invoice_id} → "
        f"Vendor: {vendor}, Amount: ${total_amount:.2f}, "
        f"Confidence: {confidence_score:.0%}"
    )
    
    return {
        "invoice_id": invoice_id,
        "vendor": vendor,
        "total_amount": total_amount,
        "invoice_date": invoice_date,
        "confidence_score": confidence_score,
        "page_count": len(page_results),
    }
