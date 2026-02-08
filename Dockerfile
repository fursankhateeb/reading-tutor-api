# Force rebuild - change this number to bust cache
ARG CACHE_BUST=6

FROM python:3.11-slim
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    make \
    build-essential \
    libssl-dev \
    ca-certificates \
    libasound2 \
    libgomp1 \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip cache purge || true
RUN pip install --no-cache-dir --force-reinstall -r requirements.txt

# Copy application code
COPY app/ ./app/

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8000

# Start application
CMD ["uvicorn", "app.api.main:app", "--host", "0.0.0.0", "--port", "8000"]