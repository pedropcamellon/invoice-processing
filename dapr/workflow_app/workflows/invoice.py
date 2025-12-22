from __future__ import annotations

import json
from datetime import timedelta
from typing import Any, Dict, Iterable, List

from dapr.clients import DaprClient
from dapr.ext.workflow import DaprWorkflowContext, WorkflowActivityContext, RetryPolicy

from shared.models import InvoiceRequest, PageMetadata, UploadResult

UPLOAD_APP_ID = "upload-service"
SPLIT_APP_ID = "split-service"
EXTRACT_APP_ID = "extract-service"
AGGREGATE_APP_ID = "aggregate-service"

retry_policy = RetryPolicy(max_number_of_attempts=3, first_retry_interval=timedelta(seconds=1))


def _invoke_service(app_id: str, method: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    with DaprClient() as client:
        response = client.invoke_method(
            app_id=app_id,
            method_name=method,
            data=json.dumps(payload).encode("utf-8"),
            content_type="application/json",
            http_verb="POST",
        )
        return json.loads(response.text())


def upload_pdf_activity(ctx: WorkflowActivityContext, payload: Dict[str, Any]) -> Dict[str, Any]:
    request = InvoiceRequest(**payload)
    return _invoke_service(UPLOAD_APP_ID, "upload", request.model_dump())


def split_pdf_activity(ctx: WorkflowActivityContext, payload: Dict[str, Any]) -> Dict[str, Any]:
    upload = UploadResult(**payload)
    return _invoke_service(SPLIT_APP_ID, "split", upload.model_dump())


def extract_invoice_activity(ctx: WorkflowActivityContext, payload: Dict[str, Any]) -> Dict[str, Any]:
    page = PageMetadata(**payload)
    return _invoke_service(EXTRACT_APP_ID, "extract", page.model_dump())


def aggregate_invoice_activity(ctx: WorkflowActivityContext, payload: Dict[str, Any]) -> Dict[str, Any]:
    return _invoke_service(AGGREGATE_APP_ID, "aggregate", payload)


def _chunks(iterable: List[Dict[str, Any]], size: int) -> Iterable[List[Dict[str, Any]]]:
    for idx in range(0, len(iterable), size):
        yield iterable[idx : idx + size]


def page_batch_workflow(ctx: DaprWorkflowContext, payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    pages: List[Dict[str, Any]] = payload.get("pages", [])
    results: List[Dict[str, Any]] = []
    for page in pages:
        page_result = yield ctx.call_activity(
            extract_invoice_activity, input=page, retry_policy=retry_policy
        )
        results.append(page_result)
    return results


def invoice_workflow(ctx: DaprWorkflowContext, wf_input: Dict[str, Any]) -> Dict[str, Any]:
    request = InvoiceRequest(**wf_input)

    upload_result = yield ctx.call_activity(
        upload_pdf_activity, input=request.model_dump(), retry_policy=retry_policy
    )

    split_result = yield ctx.call_activity(
        split_pdf_activity, input=upload_result, retry_policy=retry_policy
    )

    pages: List[Dict[str, Any]] = split_result.get("pages", [])
    page_summaries: List[Dict[str, Any]] = []

    if len(pages) <= 2:
        for page in pages:
            page_summary = yield ctx.call_activity(
                extract_invoice_activity, input=page, retry_policy=retry_policy
            )
            page_summaries.append(page_summary)
    else:
        child_tasks = [
            ctx.call_child_workflow(
                page_batch_workflow,
                input={"pages": batch},
                retry_policy=retry_policy,
            )
            for batch in _chunks(pages, size=2)
        ]
        for task in child_tasks:
            batch_result = yield task
            page_summaries.extend(batch_result)

    aggregate_payload = {"invoice_id": request.invoice_id, "pages": page_summaries}
    final_result = yield ctx.call_activity(
        aggregate_invoice_activity, input=aggregate_payload, retry_policy=retry_policy
    )
    return final_result
