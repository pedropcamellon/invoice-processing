"""
Extract Invoice Service - Extracts invoice data from page images via mock LLM.

Activity: extract_invoice_activity
Task Queue: extract-invoice-q
"""

from typing import Any
from temporalio import activity


@activity.defn
async def extract_invoice_activity(payload: dict[str, Any]) -> dict[str, Any]:
    """
    Extract invoice data from a page image (mock LLM).
    
    Input:
        - invoice_id: str
        - page_number: int
        - image_path: str
    
    Returns:
        - invoice_id: str
        - page_number: int
        - success: bool
        - vendor: str | None
        - amount: float | None
        - date: str | None
        - error: str | None
    """
    invoice_id = payload.get("invoice_id")
    page_number = payload.get("page_number")
    image_path = payload.get("image_path")
    
    # Mock LLM extraction
    mock_data = {
        1: {"vendor": "ACME Corp", "amount": 1500.50, "date": "2024-12-01"},
        2: {"vendor": "ACME Corp", "amount": 0.00, "date": "2024-12-01"},
        3: {"vendor": "ACME Corp", "amount": 0.00, "date": "2024-12-01"},
    }
    
    extracted = mock_data.get(page_number, {})
    
    print(
        f"[EXTRACT_INVOICE] Page {page_number} → "
        f"Vendor: {extracted.get('vendor')}, Amount: {extracted.get('amount')}"
    )
    
    return {
        "invoice_id": invoice_id,
        "page_number": page_number,
        "success": True,
        "vendor": extracted.get("vendor"),
        "amount": extracted.get("amount"),
        "date": extracted.get("date"),
        "error": None,
    }
