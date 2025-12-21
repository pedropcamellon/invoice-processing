"""
Upload PDF Service - Handles uploading invoice PDFs to blob storage.

Activity: upload_pdf_activity
Task Queue: upload-pdf-q
"""

from typing import Any
from temporalio import activity

# Mock blob storage for POC
MOCK_BLOB_STORAGE = {}


@activity.defn
async def upload_pdf_activity(payload: dict[str, Any]) -> dict[str, Any]:
    """
    Upload PDF bytes to blob storage.
    
    Input:
        - invoice_id: str
        - pdf_bytes: bytes (base64 encoded)
    
    Returns:
        - invoice_id: str
        - blob_path: str
        - file_size: int
    """
    invoice_id = payload.get("invoice_id")
    pdf_bytes = payload.get("pdf_bytes", "")
    
    # Mock: store in memory
    blob_path = f"pdfs/{invoice_id}.pdf"
    file_size = len(pdf_bytes) if isinstance(pdf_bytes, bytes) else len(pdf_bytes.encode())
    
    MOCK_BLOB_STORAGE[blob_path] = pdf_bytes
    
    print(f"[UPLOAD_PDF] Uploaded {blob_path} ({file_size} bytes)")
    
    return {
        "invoice_id": invoice_id,
        "blob_path": blob_path,
        "file_size": file_size,
    }
