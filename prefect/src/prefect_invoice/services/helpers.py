"""Shared helpers for Prefect service tasks."""

from __future__ import annotations

import random
import string


def generate_blob_path(invoice_id: str, suffix: str = "pdf") -> str:
    token = "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
    return f"invoices/{invoice_id}/{token}.{suffix}"
