FROM python:3.10-slim-bookworm

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential cmake \
    libopenblas-dev liblapack-dev \
    libgl1 libglib2.0-0 libsm6 libxext6 libxrender1 \
    && rm -rf /var/lib/apt/lists/*

COPY Silent-Face-Anti-Spoofing-master /app/Silent-Face-Anti-Spoofing-master
COPY FaceRecognition/requirements.txt /app/FaceRecognition/requirements.txt

RUN pip install --no-cache-dir -r /app/FaceRecognition/requirements.txt

COPY FaceRecognition /app/FaceRecognition

WORKDIR /app/FaceRecognition

ENV PYTHONUNBUFFERED=1
ENV SPOOFING_DEVICE_ID=0
ENV FLASK_DEBUG=false

EXPOSE 5000

CMD ["python", "app.py"]
