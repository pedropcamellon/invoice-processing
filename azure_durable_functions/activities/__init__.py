"""
Activities package for invoice processing workflow.

This module exports all activity blueprints for registration in the main app.
"""

from .upload_pdf import upload_pdf_bp
from .split_pdf import split_pdf_bp
from .extract_invoice import extract_invoice_bp
from .aggregate_invoice import aggregate_invoice_bp

# Export all blueprints as a list for easy registration
activity_blueprints = [
    upload_pdf_bp,
    split_pdf_bp,
    extract_invoice_bp,
    aggregate_invoice_bp,
]

__all__ = [
    "upload_pdf_bp",
    "split_pdf_bp",
    "extract_invoice_bp",
    "aggregate_invoice_bp",
    "activity_blueprints",
]
