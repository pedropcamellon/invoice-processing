"""Service-specific Prefect tasks.

Each module maps to a logical microservice to keep responsibilities isolated
and encourage independent evolution of implementations.
"""

from .aggregate_invoice import aggregate_invoice_activity
from .extract_invoice import extract_invoice_activity
from .split_pdf import split_pdf_activity
from .upload_pdf import upload_pdf_activity

__all__ = [
    "aggregate_invoice_activity",
    "extract_invoice_activity",
    "split_pdf_activity",
    "upload_pdf_activity",
]
