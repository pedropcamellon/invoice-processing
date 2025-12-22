from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

from dapr.clients import DaprClient
from dapr.clients.exceptions import DaprInternalError
from dapr.ext.workflow import WorkflowRuntime

from shared.models import InvoiceRequest

from workflows.invoice import (
    aggregate_invoice_activity,
    invoice_workflow,
    page_batch_workflow,
    split_pdf_activity,
    upload_pdf_activity,
    extract_invoice_activity,
)

WORKFLOW_COMPONENT = "dapr"
WORKFLOW_NAME = "invoice_workflow"

app = FastAPI(title="Workflow App", version="0.1.0")

workflow_runtime = WorkflowRuntime()
workflow_runtime.register_workflow(invoice_workflow)
workflow_runtime.register_workflow(page_batch_workflow)
workflow_runtime.register_activity(upload_pdf_activity)
workflow_runtime.register_activity(split_pdf_activity)
workflow_runtime.register_activity(extract_invoice_activity)
workflow_runtime.register_activity(aggregate_invoice_activity)

_runtime_started = False


@app.on_event("startup")
async def on_startup() -> None:
    global _runtime_started
    if not _runtime_started:
        workflow_runtime.start()
        _runtime_started = True


@app.on_event("shutdown")
async def on_shutdown() -> None:
    global _runtime_started
    if _runtime_started:
        workflow_runtime.shutdown()
        _runtime_started = False


@app.post("/api/workflows/invoice")
async def start_invoice_workflow(request: InvoiceRequest):
    instance_id = request.invoice_id
    with DaprClient() as client:
        response = client.start_workflow(
            instance_id=instance_id,
            workflow_component=WORKFLOW_COMPONENT,
            workflow_name=WORKFLOW_NAME,
            input=request.model_dump(),
        )
    return {"instance_id": response.instance_id}


@app.get("/api/workflows/{instance_id}")
async def get_workflow(instance_id: str):
    try:
        with DaprClient() as client:
            response = client.get_workflow(
                instance_id=instance_id, workflow_component=WORKFLOW_COMPONENT
            )
    except DaprInternalError as exc:  # pragma: no cover - best effort surfacing
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return {
        "instance_id": response.instance_id,
        "name": response.workflow_name,
        "status": response.runtime_status,
        "created_at": response.created_at.ToJsonString() if response.created_at else None,
        "last_updated_at": response.last_updated_at.ToJsonString()
        if response.last_updated_at
        else None,
    }


@app.post("/api/workflows/{instance_id}/raise-event/{event_name}")
async def raise_event(instance_id: str, event_name: str, payload: dict):
    with DaprClient() as client:
        client.raise_workflow_event(
            instance_id=instance_id,
            workflow_component=WORKFLOW_COMPONENT,
            event_name=event_name,
            event_data=payload,
        )
    return JSONResponse({"status": "raised"})


@app.post("/api/workflows/{instance_id}/terminate")
async def terminate_workflow(instance_id: str):
    with DaprClient() as client:
        client.terminate_workflow(
            instance_id=instance_id,
            workflow_component=WORKFLOW_COMPONENT,
        )
    return JSONResponse({"status": "terminated"})


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="0.0.0.0", port=8080, reload=False)
