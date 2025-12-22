"""Prefect flow that orchestrates invoice processing."""

from __future__ import annotations

from prefect import flow

from .models import FinalInvoice, InvoiceInput
from .services import (
    aggregate_invoice_activity,
    extract_invoice_activity,
    split_pdf_activity,
    upload_pdf_activity,
)


@flow(name="invoice-processing-flow")
def invoice_processing_flow(invoice: InvoiceInput) -> FinalInvoice:
    """Fan-out/fan-in invoice orchestration implemented with Prefect."""

    upload_result = upload_pdf_activity.submit(invoice)
    split_result = split_pdf_activity.submit(upload_result)

    extraction_futures = []
    for idx, page_path in enumerate(split_result.result().page_paths, start=1):
        extraction_futures.append(
            extract_invoice_activity.submit(
                invoice_id=invoice.invoice_id,
                page_number=idx,
                image_path=page_path,
            )
        )

    extraction_results = [future.result() for future in extraction_futures]

    final_invoice_future = aggregate_invoice_activity.submit(
        invoice_id=invoice.invoice_id,
        page_results=extraction_results,
    )
    return final_invoice_future.result()
