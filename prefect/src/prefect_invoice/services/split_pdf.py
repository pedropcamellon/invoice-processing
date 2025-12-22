"""Split PDF service task."""

from __future__ import annotations

from prefect import task

from ..models import SplitResult, UploadResult
from .helpers import generate_blob_path


@task(name="split_pdf_activity")
def split_pdf_activity(upload_result: UploadResult) -> SplitResult:
    """Fake PDF splitting service returning page image paths."""

    page_count = 3
    page_paths = [
        generate_blob_path(upload_result.invoice_id, suffix=f"page-{i:02d}.png")
        for i in range(1, page_count + 1)
    ]
    return SplitResult(
        invoice_id=upload_result.invoice_id,
        page_count=page_count,
        page_paths=page_paths,
    )
