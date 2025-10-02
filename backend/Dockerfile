# syntax=docker/dockerfile:1
FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# System deps (keep minimal). Uncomment extras if you want PDF OCR support in container.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    wget \
    ca-certificates \
    poppler-utils \
    tesseract-ocr \
    tesseract-ocr-eng \
    ghostscript \
    pandoc \
  && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
# Install PyTorch CPU wheels for transformers-based VLMs, then app deps
RUN pip install --no-cache-dir --extra-index-url https://download.pytorch.org/whl/cpu torch==2.3.1 \
 && pip install --no-cache-dir -r requirements.txt

COPY app ./app

# Ensure runtime dirs exist (also mounted as volumes in compose)
RUN mkdir -p /app/uploads /app/artifacts

EXPOSE 8000

CMD ["python", "-m", "app.main"]
