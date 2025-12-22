from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from shared.models import LineItem, PageExtraction, PageMetadata

app = FastAPI(title="Extract Service", version="0.1.0")


def _mock_line_items(page: PageMetadata) -> list[LineItem]:
    base = 100.0 + (page.page_number * 5)
    return [
        LineItem(
            description=f"Page {page.page_number} line 1",
            quantity=1,
            unit_price=base,
            amount=base,
        ),
        LineItem(
            description=f"Page {page.page_number} line 2",
            quantity=2,
            unit_price=base / 2,
            amount=base,
        ),
    ]


@app.post("/extract", response_model=PageExtraction)
async def extract_page(page: PageMetadata) -> PageExtraction:
    line_items = _mock_line_items(page)
    total_amount = sum(item.amount for item in line_items)
    vendor = f"Vendor-{page.invoice_id[:4].upper()}"
    confidence = 0.85 + (page.page_number * 0.02)
    return PageExtraction(
        invoice_id=page.invoice_id,
        page_number=page.page_number,
        vendor=vendor,
        total_amount=round(total_amount, 2),
        line_items=line_items,
        confidence=min(confidence, 0.99),
    )


@app.get("/health")
async def health() -> JSONResponse:
    return JSONResponse({"status": "ok"})


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="0.0.0.0", port=7301, reload=False)
