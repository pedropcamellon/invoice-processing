from __future__ import annotations

import os
import shutil
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

from shared.models import InvoiceRequest, UploadResult

SOURCE_BASE_DIR = Path(os.getenv("SOURCE_BASE_DIR", "/data"))
ARTIFACT_ROOT = Path(os.getenv("ARTIFACT_DIR", "/artifacts"))

app = FastAPI(title="Upload Service", version="0.1.0")

BLOB_ROOT = ARTIFACT_ROOT / "blobs"
BLOB_ROOT.mkdir(parents=True, exist_ok=True)


def _ensure_pdf(request: InvoiceRequest) -> Path:
    if not request.pdf_path:
        raise HTTPException(status_code=400, detail="pdf_path is required for upload")
    requested_path = Path(request.pdf_path)
    source_path = requested_path if requested_path.is_absolute() else (SOURCE_BASE_DIR / requested_path).resolve()
    if not source_path.exists():
        raise HTTPException(status_code=404, detail=f"PDF not found: {request.pdf_path}")
    return source_path


def _determine_page_count(source: Path) -> int:
    size_kb = max(source.stat().st_size // 1024, 1)
    return max(1, min(5, size_kb // 32 + 1))


@app.post("/upload", response_model=UploadResult)
async def upload_invoice(request: InvoiceRequest) -> UploadResult:
    source_path = _ensure_pdf(request)
    target_dir = BLOB_ROOT / request.invoice_id
    target_dir.mkdir(parents=True, exist_ok=True)
    target_file = target_dir / source_path.name
    shutil.copyfile(source_path, target_file)

    page_count = _determine_page_count(source_path)
    relative_blob = str(target_file.relative_to(ARTIFACT_ROOT))
    return UploadResult(
        invoice_id=request.invoice_id,
        blob_path=relative_blob,
        original_filename=source_path.name,
        page_count=page_count,
    )


@app.get("/healthz")
async def health() -> JSONResponse:
    return JSONResponse({"status": "ok"})


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="0.0.0.0", port=7101, reload=False)
