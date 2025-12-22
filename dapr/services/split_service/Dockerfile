FROM python:3.11-slim

WORKDIR /app

# Install uv for fast dependency installation
RUN pip install --no-cache-dir uv

# Install shared package first
COPY shared ./shared
RUN uv pip install --system ./shared

# Copy service code and install dependencies
COPY services/split_service/pyproject.toml .
COPY services/split_service/app.py .
RUN uv pip install --system .

# Create artifact directories
RUN mkdir -p /artifacts/images

ENV ARTIFACT_DIR=/artifacts

EXPOSE 7201

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "7201"]
