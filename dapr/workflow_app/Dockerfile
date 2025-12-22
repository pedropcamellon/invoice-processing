FROM python:3.11-slim

WORKDIR /app

# Install uv for fast dependency installation
RUN pip install --no-cache-dir uv

# Install shared package first
COPY shared ./shared
RUN uv pip install --system ./shared

# Copy workflow app code and install dependencies
COPY workflow_app/pyproject.toml .
COPY workflow_app/app.py .
COPY workflow_app/workflows ./workflows
RUN uv pip install --system .

EXPOSE 8080

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080"]
