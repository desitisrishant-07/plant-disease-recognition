FROM python:3.11-slim

# System deps for Pillow
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libjpeg-dev \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Upgrade pip first
RUN pip install --no-cache-dir --upgrade pip

# Install from requirements.txt
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# EXPLICIT install — guarantee PyMySQL even if requirements.txt fails
RUN pip install --no-cache-dir PyMySQL cryptography

# Verify pymysql is importable (build will fail here if broken)
RUN python -c "import pymysql; print('PyMySQL OK:', pymysql.__version__)"

# Copy app code
COPY . .

# Create upload dirs
RUN mkdir -p uploadimages/history

ENV PORT=8080
EXPOSE 8080

CMD gunicorn --bind 0.0.0.0:${PORT} --workers 2 --threads 4 --timeout 120 app:app