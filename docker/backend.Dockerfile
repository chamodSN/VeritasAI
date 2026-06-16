# Stage 1: dependency builder
FROM python:3.11-slim AS builder

WORKDIR /build

# Install build deps for packages that compile C extensions
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --prefix=/install --no-cache-dir -r requirements.txt

# Download spaCy model during build (not at runtime)
RUN python -m spacy download en_core_web_sm --target /install


#  Stage 2: runtime
FROM python:3.11-slim AS runtime

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Create non-root user (security best practice)
RUN useradd -m -u 1000 appuser && \
    mkdir -p /app/logs && \
    chown -R appuser:appuser /app

USER appuser

# Copy application code
COPY --chown=appuser:appuser . .

# Health check - used by docker compose and orchestrators
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/health').raise_for_status()"

EXPOSE 8000

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]