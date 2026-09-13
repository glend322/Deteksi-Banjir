FROM python:3.11-slim

# Install system dependencies (psycopg2 butuh libpq)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libpq-dev \
        gcc \
        gdal-bin \
        libgdal-dev && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements dulu (layer cache-friendly)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Buat direktori uploads
RUN mkdir -p uploads

EXPOSE 8000

# Jalankan dengan uvicorn (4 workers untuk production)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
