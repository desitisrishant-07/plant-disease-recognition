FROM python:3.11-slim

# curl install karein
RUN apt-get update && apt-get install -y curl

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Models folder banayein (agar pehle se nahi hai)
RUN mkdir -p models

# MODEL DOWNLOAD KAREIN (Yahan apna Step 1 wala link daalein)
RUN curl -L -o models/plant_disease_recog_model_pwp.keras "https://media.githubusercontent.com/media/desitisrishant-07/plant-disease-recognition/main/models/plant_disease_recog_model_pwp.keras"

# Verification: Check karein ki file download hui hai aur uska size kya hai
RUN ls -lh models/plant_disease_recog_model_pwp.keras

# Gunicorn start karein
CMD gunicorn app:app --bind 0.0.0.0:$PORT --workers 1 --threads 4 --timeout 120