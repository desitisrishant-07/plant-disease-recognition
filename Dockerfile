FROM python:3.11-slim

# wget install karein (model download karne ke liye)
RUN apt-get update && apt-get install -y wget

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Model ko GitHub LFS se download karein
# NOTE: Niche URL mein "desit" aur "plant-disease-recognition" aapke GitHub username aur repo name se match hone chahiye.
RUN wget -O models/plant_disease_recog_model_pwp.keras https://media.githubusercontent.com/media/desitisrishant-07/plant-disease-recognition/main/models/plant_disease_recog_model_pwp.keras

# Gunicorn start karein
CMD gunicorn app:app --bind 0.0.0.0:$PORT --workers 1 --threads 4 --timeout 120