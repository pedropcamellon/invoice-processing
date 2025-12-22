from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

from shared.models import PageMetadata, SplitResult, UploadResult

ARTIFACT_ROOT = Path(os.getenv("ARTIFACT_DIR", "/artifacts"))

app = FastAPI(title="Split Service", version="0.1.0")

IMAGES_ROOT = (ARTIFACT_ROOT / "images").resolve()
IMAGES_ROOT.mkdir(parents=True, exist_ok=True)


@app.post("/split", response_model=SplitResult)
async def split_pdf(upload: UploadResult) -> SplitResult:
    if upload.page_count <= 0:
        raise HTTPException(status_code=400, detail="page_count must be > 0")

    invoice_dir = IMAGES_ROOT / upload.invoice_id
    invoice_dir.mkdir(parents=True, exist_ok=True)

    pages: list[PageMetadata] = []
    for idx in range(upload.page_count):
        page_num = idx + 1
        image_path = invoice_dir / f"page_{page_num}.png"
        image_path.write_text("placeholder image bytes", encoding="utf-8")
        pages.append(
            PageMetadata(
                invoice_id=upload.invoice_id,
                page_number=page_num,
                blob_path=upload.blob_path,
                image_path=str(image_path.relative_to(ARTIFACT_ROOT)),
            )
        )

    return SplitResult(invoice_id=upload.invoice_id, pages=pages)


@app.get("/healthz")
async def health() -> JSONResponse:
    return JSONResponse({"status": "ok"})


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="0.0.0.0", port=7201, reload=False)
