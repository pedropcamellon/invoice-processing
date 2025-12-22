from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field, HttpUrl


class InvoiceRequest(BaseModel):
    """Top-level workflow input."""

    invoice_id: str = Field(..., description="Business identifier used as workflow instance ID")
    pdf_path: Optional[str] = Field(
        default=None, description="Path to a local PDF file relative to the repo root"
    )
    pdf_url: Optional[HttpUrl] = Field(default=None, description="Remote PDF URL (future use)")


class UploadResult(BaseModel):
    invoice_id: str
    blob_path: str
    original_filename: str
    page_count: int


class PageMetadata(BaseModel):
    invoice_id: str
    page_number: int
    blob_path: str
    image_path: str


class SplitResult(BaseModel):
    invoice_id: str
    pages: List[PageMetadata]


class LineItem(BaseModel):
    description: str
    quantity: int
    unit_price: float
    amount: float


class PageExtraction(BaseModel):
    invoice_id: str
    page_number: int
    vendor: Optional[str]
    total_amount: Optional[float]
    line_items: List[LineItem]
    confidence: float


class AggregatedInvoice(BaseModel):
    invoice_id: str
    vendor: Optional[str]
    total_amount: float
    page_count: int
    line_items: List[LineItem]
    per_page_summary: List[PageExtraction]


__all__ = [
    "AggregatedInvoice",
    "InvoiceRequest",
    "LineItem",
    "PageExtraction",
    "PageMetadata",
    "SplitResult",
    "UploadResult",
]
