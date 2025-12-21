"""
Activity: Aggregate all extracted page data into final invoice structure
"""

import azure.durable_functions as df
import time
import logging
from datetime import datetime
from typing import Any, Dict

aggregate_invoice_bp = df.Blueprint()


@aggregate_invoice_bp.activity_trigger(input_name="payload")
def aggregate_invoice_data(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Activity: Aggregate all extracted page data into final invoice structure

    In production, this would:
    - Combine data from all pages
    - Resolve conflicts or duplicates
    - Validate totals and calculations
    - Store in database
    - Generate final report
    """
    invoice_id = payload.get("invoice_id")
    pages = payload.get("pages", [])
    metadata = payload.get("metadata", {})

    logging.info(f"[ACTIVITY:AGGREGATE] Aggregating data for {invoice_id}")
    logging.info(f"[ACTIVITY:AGGREGATE] Processing {len(pages)} pages of data")

    # Simulate aggregation processing
    time.sleep(1)

    # Organize data by section
    header_data = {}
    line_items = []
    summary_data = {}

    total_confidence = 0
    total_processing_time = 0

    for page in pages:
        section = page.get("section")
        data = page.get("data", {})

        if section == "header":
            header_data.update(data)
        elif section == "line_items":
            line_items.extend(data.get("items", []))
        elif section == "summary":
            summary_data.update(data)

        total_processing_time += page.get("processing_time_seconds", 0)

    # Build final invoice structure
    final_invoice = {
        "invoice_id": invoice_id,
        "processing_timestamp": datetime.utcnow().isoformat(),
        "status": "completed",
        "header": header_data,
        "line_items": line_items,
        "summary": summary_data,
        "metadata": metadata,
        "processing_stats": {
            "total_pages": len(pages),
            "average_confidence": round(total_confidence / len(pages), 2)
            if pages
            else 0,
            "total_processing_time_seconds": round(total_processing_time, 2),
        },
    }

    logging.info(f"[ACTIVITY:AGGREGATE] Aggregation complete for {invoice_id}")
    logging.info(f"[ACTIVITY:AGGREGATE] Total line items: {len(line_items)}")

    return final_invoice
