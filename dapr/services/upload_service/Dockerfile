FROM python:3.11-slim

WORKDIR /app

# Install uv for fast dependency installation
RUN pip install --no-cache-dir uv

# Install shared package first
COPY shared ./shared
RUN uv pip install --system ./shared

# Copy service code and install dependencies
COPY services/upload_service/pyproject.toml .
COPY services/upload_service/app.py .
RUN uv pip install --system .

# Create artifact directories
RUN mkdir -p /artifacts/blobs /data

ENV ARTIFACT_DIR=/artifacts
ENV SOURCE_BASE_DIR=/data

EXPOSE 7101

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "7101"]
