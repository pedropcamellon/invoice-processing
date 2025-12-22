"""Upload PDF service task."""

from __future__ import annotations

from prefect import task

from ..models import InvoiceInput, UploadResult
from .helpers import generate_blob_path


@task(name="upload_pdf_activity")
def upload_pdf_activity(invoice: InvoiceInput) -> UploadResult:
    """Pretend to upload the PDF to blob storage."""

    blob_path = generate_blob_path(invoice.invoice_id)
    return UploadResult(
        invoice_id=invoice.invoice_id,
        blob_path=blob_path,
        file_size=len(invoice.pdf_bytes),
    )
