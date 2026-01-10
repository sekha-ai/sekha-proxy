FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY proxy.py .
COPY config.py .
COPY context_injection.py .
COPY health.py .

# Expose proxy port
EXPOSE 8081

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD python -c "import httpx; httpx.get('http://localhost:8081/health', timeout=5)"

# Run proxy
CMD ["python", "proxy.py"]
