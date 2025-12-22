from __future__ import annotations

from typing import List

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from shared.models import AggregatedInvoice, LineItem, PageExtraction

app = FastAPI(title="Aggregate Service", version="0.1.0")


class AggregateRequest(BaseModel):
    invoice_id: str
    pages: List[PageExtraction]


@app.post("/aggregate", response_model=AggregatedInvoice)
async def aggregate_invoice(payload: AggregateRequest) -> AggregatedInvoice:
    if not payload.pages:
        raise HTTPException(status_code=400, detail="pages are required")

    vendor = next((page.vendor for page in payload.pages if page.vendor), None)
    line_items: list[LineItem] = []
    total_amount = 0.0
    for page in payload.pages:
        line_items.extend(page.line_items)
        total_amount += page.total_amount or sum(item.amount for item in page.line_items)

    return AggregatedInvoice(
        invoice_id=payload.invoice_id,
        vendor=vendor,
        total_amount=round(total_amount, 2),
        page_count=len(payload.pages),
        line_items=line_items,
        per_page_summary=payload.pages,
    )


@app.get("/healthz")
async def health() -> JSONResponse:
    return JSONResponse({"status": "ok"})


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="0.0.0.0", port=7401, reload=False)
