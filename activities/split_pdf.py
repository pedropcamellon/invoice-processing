"""
Activity: Split PDF into individual page images
"""

import azure.durable_functions as df
import logging
from typing import Any, Dict, List

import storage_helper

split_pdf_bp = df.Blueprint()


@split_pdf_bp.activity_trigger(input_name="payload")
def split_pdf_to_images(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Activity: Split PDF into individual page images and upload to Azurite

    Uses PyMuPDF (fitz) to:
    1. Download PDF from Azurite blob URL
    2. Convert each page to PNG image
    3. Upload each image to Azurite blob storage
    4. Return list of page metadata with blob URLs
    """
    import fitz  # PyMuPDF

    invoice_id = payload.get("invoice_id")
    pdf_id = payload.get("pdf_id")
    pdf_blob_url = payload.get("pdf_blob_url")

    logging.info(f"[ACTIVITY:SPLIT_PDF] Processing PDF: {invoice_id}")
    logging.info(f"[ACTIVITY:SPLIT_PDF] Downloading PDF from: {pdf_blob_url}")

    # Download PDF from Azurite
    pdf_data = storage_helper.download_blob(pdf_blob_url)
    logging.info(f"[ACTIVITY:SPLIT_PDF] Downloaded PDF: {len(pdf_data)} bytes")

    # Open PDF with PyMuPDF
    pdf_document = fitz.open(stream=pdf_data, filetype="pdf")
    page_count = len(pdf_document)
    logging.info(f"[ACTIVITY:SPLIT_PDF] PDF has {page_count} pages")

    # Convert each page to image and upload
    pages = []
    for page_num in range(page_count):
        logging.info(
            f"[ACTIVITY:SPLIT_PDF] Converting page {page_num + 1}/{page_count} to image..."
        )

        # Get page
        page = pdf_document[page_num]

        # Render page to image (at 2x resolution for better quality)
        # zoom=2.0 means 2x scaling (144 DPI instead of default 72 DPI)
        mat = fitz.Matrix(2.0, 2.0)
        pix = page.get_pixmap(matrix=mat)

        # Convert to PNG bytes
        image_data = pix.tobytes("png")
        logging.info(
            f"[ACTIVITY:SPLIT_PDF] Page {page_num + 1} image: {len(image_data)} bytes, {pix.width}x{pix.height}px"
        )

        # Upload image to Azurite
        image_blob_url = storage_helper.upload_page_image(image_data, pdf_id, page_num)
        logging.info(
            f"[ACTIVITY:SPLIT_PDF] Page {page_num + 1} uploaded: {image_blob_url}"
        )

        # Create page metadata
        page_data = {
            "invoice_id": invoice_id,
            "page_number": page_num,
            "total_pages": page_count,
            "image_url": image_blob_url,
            "image_size": f"{pix.width}x{pix.height}",
        }
        pages.append(page_data)

    # Close PDF document
    pdf_document.close()

    logging.info(f"[ACTIVITY:SPLIT_PDF] Successfully processed {page_count} pages")
    return pages
