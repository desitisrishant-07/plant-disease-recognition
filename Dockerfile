FROM python:3.11-slim

# System deps for Pillow
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libjpeg-dev \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps first (layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code
COPY . .

# Create upload directories
RUN mkdir -p uploadimages/history

# Railway uses PORT env var
ENV PORT=8080
EXPOSE 8080

# Gunicorn start
CMD gunicorn --bind 0.0.0.0:${PORT} --workers 2 --threads 4 --timeout 120 app:app