from __future__ import annotations

import azure.functions as func
import azure.durable_functions as df
import logging
import json

import storage_helper

# Import activity blueprints
from activities import activity_blueprints

myApp = df.DFApp(http_auth_level=func.AuthLevel.ANONYMOUS)

# Register all activity blueprints
for bp in activity_blueprints:
    myApp.register_functions(bp)

# ============================================================================
# region HTTP TRIGGERS
# ============================================================================


@myApp.route(route="invoice/process", methods=["POST"])
@myApp.durable_client_input(client_name="client")
async def process_invoice(req: func.HttpRequest, client):
    """
    Start invoice processing workflow

    POST /api/invoice/process
    Body: {
        "invoice_id": "INV-2025-001",
        "pdf_url": "https://storage.example.com/invoices/invoice.pdf",  (optional)
        "pdf_base64": "JVBERi0xLjQKJeLjz9MK...",  (optional)
        "pdf_path": "c:/path/to/invoice.pdf",  (optional)
        "metadata": {
            "customer": "Acme Corp",
            "upload_date": "2025-11-03"
        }
    }

    Supports three modes:
    1. PDF URL (pdf_url) - URL to download PDF from
    2. PDF Base64 (pdf_base64) - Base64-encoded PDF content
    3. PDF Path (pdf_path) - Local file system path
    """
    try:
        req_body = req.get_json()
        invoice_id = req_body.get("invoice_id")
        pdf_url = req_body.get("pdf_url")
        pdf_base64 = req_body.get("pdf_base64")
        pdf_path = req_body.get("pdf_path")
        metadata = req_body.get("metadata", {})

        if not invoice_id:
            return func.HttpResponse(
                json.dumps({"error": "Missing invoice_id"}),
                status_code=400,
                mimetype="application/json",
            )

        if not (pdf_url or pdf_base64 or pdf_path):
            return func.HttpResponse(
                json.dumps(
                    {
                        "error": "Missing PDF source: provide pdf_url, pdf_base64, or pdf_path"
                    }
                ),
                status_code=400,
                mimetype="application/json",
            )

        # Start the invoice processing orchestration
        input_data = {
            "invoice_id": invoice_id,
            "pdf_url": pdf_url,
            "pdf_base64": pdf_base64,
            "pdf_path": pdf_path,
            "metadata": metadata,
        }

        instance_id = await client.start_new(
            "invoice_orchestrator", client_input=input_data
        )
        response = client.create_check_status_response(req, instance_id)

        return response

    except ValueError:
        return func.HttpResponse(
            json.dumps({"error": "Invalid JSON body"}),
            status_code=400,
            mimetype="application/json",
        )


# ============================================================================
# endregion HTTP TRIGGERS
# ============================================================================


# ============================================================================
# region ORCHESTRATORS
# ============================================================================


@myApp.orchestration_trigger(context_name="context")
def invoice_orchestrator(context: df.DurableOrchestrationContext):
    """
    Main orchestrator for invoice processing

    Workflow:
    1. Upload PDF to Azurite blob storage
    2. Split PDF into pages/images (also uploads to storage)
    3. Process each page in parallel (fan-out/fan-in)
    4. Aggregate results
    5. Return final invoice data
    """
    input_data = context.get_input()
    invoice_id = input_data.get("invoice_id")
    pdf_url = input_data.get("pdf_url")
    pdf_base64 = input_data.get("pdf_base64")
    pdf_path = input_data.get("pdf_path")

    logging.info(f"[ORCHESTRATOR] Starting invoice processing: {invoice_id}")
    if pdf_url:
        logging.info(f"[ORCHESTRATOR] PDF URL: {pdf_url}")
    elif pdf_path:
        logging.info(f"[ORCHESTRATOR] PDF Path: {pdf_path}")
    elif pdf_base64:
        logging.info(f"[ORCHESTRATOR] PDF Base64 length: {len(pdf_base64)} chars")

    # Step 1: Upload PDF to blob storage
    logging.info("[ORCHESTRATOR] Step 1: Uploading PDF to Azurite blob storage...")
    pdf_upload_result = yield context.call_activity(
        "upload_pdf_to_storage_activity",
        {
            "invoice_id": invoice_id,
            "pdf_url": pdf_url,
            "pdf_base64": pdf_base64,
            "pdf_path": pdf_path,
        },
    )

    pdf_blob_url = pdf_upload_result.get("pdf_blob_url")
    pdf_id = pdf_upload_result.get("pdf_id")
    logging.info(f"[ORCHESTRATOR] PDF uploaded: {pdf_blob_url}")

    # Step 2: Split PDF into page images and upload to storage
    logging.info("[ORCHESTRATOR] Step 2: Splitting PDF into page images...")
    pages_data = yield context.call_activity(
        "split_pdf_to_images",
        {
            "invoice_id": invoice_id,
            "pdf_id": pdf_id,
            "pdf_blob_url": pdf_blob_url,
        },
    )

    page_count = len(pages_data)
    logging.info(f"[ORCHESTRATOR] PDF split into {page_count} page images")

    # Step 3: Process each page in parallel (FAN-OUT)
    logging.info(f"[ORCHESTRATOR] Step 3: Processing {page_count} pages in parallel...")

    # Create parallel tasks for each page
    parallel_tasks = []
    for page_data in pages_data:
        task = context.call_activity("extract_invoice_data_from_page", page_data)
        parallel_tasks.append(task)

    # Wait for all pages to complete (FAN-IN)
    extracted_data_list = yield context.task_all(parallel_tasks)

    logging.info(f"[ORCHESTRATOR] All {page_count} pages processed")

    # Step 4: Aggregate results
    logging.info("[ORCHESTRATOR] Step 4: Aggregating extracted data...")
    final_result = yield context.call_activity(
        "aggregate_invoice_data",
        {
            "invoice_id": invoice_id,
            "pages": extracted_data_list,
            "metadata": input_data.get("metadata", {}),
        },
    )

    logging.info(f"[ORCHESTRATOR] Invoice processing complete: {invoice_id}")
    logging.info(f"[ORCHESTRATOR] Final result: {final_result}")

    return final_result


# ============================================================================
# endregion ORCHESTRATORS
# ============================================================================


# ============================================================================
# region STARTUP
# ============================================================================


@myApp.function_name(name="startup")
@myApp.route(route="startup", methods=["GET"])
def startup_init(req: func.HttpRequest) -> func.HttpResponse:
    """
    Startup endpoint to initialize Azurite storage containers.
    Call this once after starting the function app to ensure containers exist.

    GET /api/startup
    """
    try:
        logging.info("[STARTUP] Initializing Azurite storage...")
        storage_helper.ensure_container_exists("pdfs")
        storage_helper.ensure_container_exists("images")
        logging.info("[STARTUP] Storage initialization complete")

        return func.HttpResponse(
            json.dumps(
                {
                    "status": "success",
                    "message": "Azurite storage initialized successfully",
                    "containers": ["pdfs", "images"],
                }
            ),
            status_code=200,
            mimetype="application/json",
        )
    except Exception as e:
        logging.error(f"[STARTUP] Error initializing storage: {str(e)}")
        return func.HttpResponse(
            json.dumps(
                {
                    "status": "error",
                    "message": f"Failed to initialize storage: {str(e)}",
                }
            ),
            status_code=500,
            mimetype="application/json",
        )
