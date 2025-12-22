"""Extract invoice service task."""

from __future__ import annotations

import random

from prefect import task

from ..models import ExtractResult


@task(name="extract_invoice_activity")
def extract_invoice_activity(invoice_id: str, page_number: int, image_path: str) -> ExtractResult:
    """Mock page-level extraction (simulating LLM/OCR inference)."""

    amount = round(100 + random.random() * 50, 2)
    vendor = random.choice(["Globex", "Initech", "Umbrella Corp"])

    return ExtractResult(
        invoice_id=invoice_id,
        page_number=page_number,
        vendor=vendor,
        amount=amount,
        date="2025-12-01",
    )
