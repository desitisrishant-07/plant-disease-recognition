FROM python:3.11-slim

# Git aur Git LFS install karein
RUN apt-get update && \
    apt-get install -y git git-lfs && \
    git lfs install

WORKDIR /app

# GitHub se seedha clone karein taaki LFS (model file) sahi se download ho
# Niche apna GitHub link daalein
RUN git clone https://github.com/desitisrishant-07/plant-disease-recognition.git .

# Check karein ki asli model download hua ya nahi (250M dikhna chahiye)
RUN ls -lh models/plant_disease_recog_model_pwp.keras

# Dependencies install karein
RUN pip install --no-cache-dir -r requirements.txt

# App start karein
CMD gunicorn app:app --bind 0.0.0.0:$PORT --workers 1 --threads 4 --timeout 120