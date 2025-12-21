"""
Split PDF Service - Splits invoices into page images.

Activity: split_pdf_activity
Task Queue: split-pdf-q
"""

from typing import Any
from temporalio import activity

# Mock blob storage (shared across services for POC)
MOCK_BLOB_STORAGE = {}


@activity.defn
async def split_pdf_activity(payload: dict[str, Any]) -> dict[str, Any]:
    """
    Split PDF into individual page images.
    
    Input:
        - invoice_id: str
        - blob_path: str (path to uploaded PDF)
    
    Returns:
        - invoice_id: str
        - page_count: int
        - page_paths: list[str] (paths to page images)
    """
    invoice_id = payload.get("invoice_id")
    blob_path = payload.get("blob_path")
    
    # Mock: simulate splitting into 3 pages
    page_count = 3
    page_paths = [
        f"images/{invoice_id}/page_1.png",
        f"images/{invoice_id}/page_2.png",
        f"images/{invoice_id}/page_3.png",
    ]
    
    # Mock: store pages
    for page_path in page_paths:
        MOCK_BLOB_STORAGE[page_path] = b"mock_image_data"
    
    print(f"[SPLIT_PDF] Split {blob_path} into {page_count} pages")
    
    return {
        "invoice_id": invoice_id,
        "page_count": page_count,
        "page_paths": page_paths,
    }
