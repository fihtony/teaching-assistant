# Backend Dockerfile for Teaching Assistant Grading System
# Optimized for smaller image size

# Build stage
FROM python:3.12-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Install poppler-utils for pdf2image (needed in production too)
RUN apt-get update && apt-get install -y --no-install-recommends \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

COPY requirements-prod.txt .
RUN pip install --no-cache-dir --user -r requirements-prod.txt

# Runtime stage
FROM python:3.12-slim

WORKDIR /app

# Install only essential runtime dependencies
# poppler-utils for pdf2image
RUN apt-get update && apt-get install -y --no-install-recommends \
    poppler-utils \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user
RUN useradd -m -u 2000 appuser

# Copy Python packages from builder (without build artifacts)
COPY --from=builder /root/.local /home/appuser/.local

# Copy application code
COPY --chown=appuser:appuser . .

# Set environment variables
ENV PATH=/home/appuser/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DATA_DIR=/app/data \
    LOGS_DIR=/app/logs

# Switch to non-root user
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8090/api/v1/greeting', timeout=5)" || exit 1

# Expose port
EXPOSE 8090

# Run application
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8090"]
