FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all application code and modules
COPY main.py .
COPY config.py .
COPY api/ ./api/
COPY core/ ./core/
COPY utils/ ./utils/
COPY services/ ./services/
COPY models/ ./models/
COPY dashboard/ ./dashboard/
COPY data/ ./data/

# Copy data files (fallback if not in data/)
COPY prices.json .
COPY users.json .

# Create logs directory
RUN mkdir -p /app/logs

# Expose port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

# Run with uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "5000"]
