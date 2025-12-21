"""
Activity: Upload PDF to Azurite blob storage
"""

import azure.durable_functions as df
import logging
import base64
from typing import Any, Dict

import storage_helper

upload_pdf_bp = df.Blueprint()


@upload_pdf_bp.activity_trigger(input_name="payload")
def upload_pdf_to_storage_activity(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Activity: Upload PDF to Azurite blob storage

    Supports three modes:
    1. PDF Path - Reads from local file system
    2. PDF URL - Downloads from URL
    3. PDF Base64 - Decodes base64 string

    Returns:
        Dict with pdf_blob_url and pdf_id
    """
    invoice_id = payload.get("invoice_id")
    pdf_url = payload.get("pdf_url")
    pdf_base64 = payload.get("pdf_base64")
    pdf_path = payload.get("pdf_path")

    logging.info(f"[ACTIVITY:UPLOAD_PDF] Uploading PDF for invoice: {invoice_id}")

    # Ensure containers exist
    storage_helper.ensure_container_exists("pdfs")
    storage_helper.ensure_container_exists("images")

    # Get PDF data based on source
    pdf_data = None
    if pdf_path:
        logging.info(f"[ACTIVITY:UPLOAD_PDF] Reading from file: {pdf_path}")
        with open(pdf_path, "rb") as f:
            pdf_data = f.read()
    elif pdf_url:
        logging.info(f"[ACTIVITY:UPLOAD_PDF] Downloading from URL: {pdf_url}")
        import urllib.request

        with urllib.request.urlopen(pdf_url) as response:
            pdf_data = response.read()
    elif pdf_base64:
        logging.info(
            f"[ACTIVITY:UPLOAD_PDF] Decoding base64 PDF ({len(pdf_base64)} chars)"
        )
        pdf_data = base64.b64decode(pdf_base64)
    else:
        raise ValueError("No PDF source provided")

    # Use invoice_id as pdf_id (clean it for blob storage)
    pdf_id = invoice_id.replace("/", "_").replace("\\", "_")

    # Upload PDF to Azurite
    blob_url = storage_helper.upload_pdf_to_storage(pdf_data, pdf_id)

    logging.info(f"[ACTIVITY:UPLOAD_PDF] PDF uploaded successfully: {blob_url}")
    logging.info(f"[ACTIVITY:UPLOAD_PDF] PDF size: {len(pdf_data)} bytes")

    return {
        "pdf_blob_url": blob_url,
        "pdf_id": pdf_id,
        "pdf_size_bytes": len(pdf_data),
    }
