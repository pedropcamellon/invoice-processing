# Orchestration Worker - Temporal workflow service
FROM python:3.11-slim

WORKDIR /app

# Install uv for fast dependency installation
RUN pip install --no-cache-dir uv

# Copy dependency file
COPY orchestration/pyproject.toml ./

# Install dependencies using uv with fallback
RUN uv pip install --system --no-cache-dir -e . 2>/dev/null || \
    uv pip install --system --no-cache-dir pydantic temporalio

COPY shared ./shared

# Copy workflow code
COPY orchestration/*.py /app/

# Run worker
CMD ["python", "worker.py"]
