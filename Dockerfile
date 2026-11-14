FROM python:3.11-slim

# Working directory set karein
WORKDIR /app

# Requirements copy karein aur install karein (isme ab TensorFlow nahi hai)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Poora project copy karein
COPY . .

# App start karein
CMD gunicorn app:app --bind 0.0.0.0:$PORT --workers 1 --threads 4 --timeout 120