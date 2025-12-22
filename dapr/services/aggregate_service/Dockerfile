FROM python:3.11-slim

WORKDIR /app

# Install uv for fast dependency installation
RUN pip install --no-cache-dir uv

# Install shared package first
COPY shared ./shared
RUN uv pip install --system ./shared

# Copy service code and install dependencies
COPY services/aggregate_service/pyproject.toml .
COPY services/aggregate_service/app.py .
RUN uv pip install --system .

EXPOSE 7401

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "7401"]
