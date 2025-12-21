# Dockerfile for Extract Invoice Service (Python)
FROM python:3.11-slim

WORKDIR /app

# Install uv for fast dependency installation
RUN pip install --no-cache-dir uv

# Copy dependency file
COPY extract_invoice/pyproject.toml ./

# Install dependencies using uv with fallback
RUN uv pip install --system --no-cache-dir -e . 2>/dev/null || \
    uv pip install --system --no-cache-dir pydantic temporalio

COPY shared ./shared

# Copy application code
COPY extract_invoice/*.py ./

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    TEMPORAL_ADDRESS=${TEMPORAL_ADDRESS:-temporal:7233} \
    TASK_QUEUE=extract-invoice-q

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import socket; socket.create_connection(('temporal', 7233), timeout=1)" || exit 1

# Run worker
CMD ["python", "worker.py"]
