FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all project files
COPY . .

# Railway ek dynamic port deta hai, usko bind karne ke liye $PORT use karte hain
# TensorFlow model load hone mein time lagta hai, isliye timeout 120 hai
CMD gunicorn app:app --bind 0.0.0.0:$PORT --workers 1 --threads 4 --timeout 120