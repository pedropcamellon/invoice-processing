"""Pydantic models shared between Prefect tasks."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class InvoiceInput(BaseModel):
    """Inbound payload for invoice processing."""

    invoice_id: str = Field(..., description="Stable identifier for the invoice run")
    pdf_filename: str = Field(..., description="Original PDF filename")
    pdf_bytes: bytes = Field(..., description="Raw PDF bytes (base64-decoded)")


class UploadResult(BaseModel):
    invoice_id: str
    blob_path: str
    file_size: int


class SplitResult(BaseModel):
    invoice_id: str
    page_count: int
    page_paths: list[str]


class ExtractResult(BaseModel):
    invoice_id: str
    page_number: int
    vendor: str | None = None
    amount: float | None = None
    date: str | None = None
    success: bool = True
    error: str | None = None


class FinalInvoice(BaseModel):
    invoice_id: str
    vendor: str | None = None
    total_amount: float | None = None
    invoice_date: str | None = None
    confidence_score: float = 0.0
    page_count: int = 0
    page_results: list[dict[str, Any]] = Field(default_factory=list)
