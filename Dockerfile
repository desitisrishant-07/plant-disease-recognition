FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libjpeg-dev \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN pip install --no-cache-dir --upgrade pip
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir PyMySQL cryptography
RUN python -c "import pymysql; print('PYMYSQL_OK')"

COPY . .

RUN mkdir -p uploadimages/history

ENV PORT=8080
EXPOSE 8080

CMD gunicorn --bind 0.0.0.0: --workers 2 --threads 4 --timeout 120 app:app
