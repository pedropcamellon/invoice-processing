"""
Activity: Extract invoice data from a single page using LLM
"""

import azure.durable_functions as df
import time
import logging
import random
from typing import Any, Dict

import storage_helper

extract_invoice_bp = df.Blueprint()


@extract_invoice_bp.activity_trigger(input_name="pagedata")
def extract_invoice_data_from_page(pagedata: Dict[str, Any]) -> Dict[str, Any]:
    """
    Activity: Extract invoice data from a single page using LLM

    Currently:
    - Downloads real page image from Azurite blob storage
    - Mocks LLM extraction (future: integrate GPT-4 Vision)

    In production, this would:
    - Call Azure OpenAI / GPT-4 Vision
    - Send page image for analysis
    - Extract structured data (line items, totals, dates, etc.)
    - Return parsed invoice data
    """
    invoice_id = pagedata.get("invoice_id")
    page_num = pagedata.get("page_number")
    image_url = pagedata.get("image_url")

    logging.info(f"[ACTIVITY:EXTRACT] Processing page {page_num} of {invoice_id}")
    logging.info(f"[ACTIVITY:EXTRACT] Image URL: {image_url}")

    # Download actual image from Azurite (proves image is available)
    try:
        image_data = storage_helper.download_blob(image_url)
        logging.info(f"[ACTIVITY:EXTRACT] Downloaded image: {len(image_data)} bytes")
        logging.info(
            "[ACTIVITY:EXTRACT] Image ready for LLM (currently mocking extraction)"
        )
    except Exception as e:
        logging.error(f"[ACTIVITY:EXTRACT] Failed to download image: {e}")
        logging.warning("[ACTIVITY:EXTRACT] Proceeding with mock data")

    # Simulate LLM API call time (2-5 seconds per page)
    processing_time = random.uniform(2, 5)
    time.sleep(processing_time)

    # Mock: Generate realistic invoice data
    mock_line_items = [
        {
            "description": "Professional Services - Consulting",
            "quantity": 40,
            "unit_price": 150.00,
            "amount": 6000.00,
        },
        {
            "description": "Software License - Annual",
            "quantity": 1,
            "unit_price": 2400.00,
            "amount": 2400.00,
        },
        {
            "description": "Support Package - Premium",
            "quantity": 12,
            "unit_price": 200.00,
            "amount": 2400.00,
        },
    ]

    # Different pages might contain different sections
    if page_num == 1:
        extracted_data = {
            "page_number": page_num,
            "section": "header",
            "data": {
                "invoice_number": f"INV-{random.randint(1000, 9999)}",
                "invoice_date": "2025-11-01",
                "due_date": "2025-11-30",
                "vendor_name": "Tech Solutions Inc.",
                "vendor_address": "123 Tech Street, San Francisco, CA 94105",
                "customer_name": "Acme Corporation",
                "customer_address": "456 Business Ave, New York, NY 10001",
            },
        }
    elif page_num == pagedata.get("total_pages"):
        extracted_data = {
            "page_number": page_num,
            "section": "summary",
            "data": {
                "subtotal": 10800.00,
                "tax": 864.00,
                "total": 11664.00,
                "payment_terms": "Net 30",
                "payment_method": "Bank Transfer",
            },
        }
    else:
        # Middle pages contain line items
        extracted_data = {
            "page_number": page_num,
            "section": "line_items",
            "data": {
                "items": mock_line_items[
                    page_num - 2 : page_num
                ]  # Different items per page
            },
        }

    extracted_data["processing_time_seconds"] = round(processing_time, 2)

    logging.info(
        f"[ACTIVITY:EXTRACT] Completed page {page_num} - Section: {extracted_data['section']}"
    )
    return extracted_data
