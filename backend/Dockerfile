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
  libgl1 \
  libglib2.0-0 \
  && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

COPY pyproject.toml requirements.txt ./
# Install PyTorch CPU wheels via uv (much faster), then app deps
# Note: requirements.txt is kept for compatibility but pyproject.toml is preferred if available
RUN uv pip install --system --extra-index-url https://download.pytorch.org/whl/cpu torch==2.3.1 \
  && uv pip install --system -r pyproject.toml

COPY app ./app

# Ensure runtime dirs exist (also mounted as volumes in compose)
RUN mkdir -p /app/uploads /app/artifacts /app/models/docling

# Pre-download Docling models at build time (layout + table structure).
# Uses DOCLING_ARTIFACTS_PATH so models are baked into the image layer.
# Runtime volume mount at /app/models/docling overrides if present.
ENV DOCLING_ARTIFACTS_PATH=/app/models/docling
ARG DOCLING_WARMUP_STRICT=1
RUN if [ "$DOCLING_WARMUP_STRICT" = "1" ]; then \
      python -c "\
from docling.document_converter import DocumentConverter; \
from docling.datamodel.pipeline_options import PdfPipelineOptions; \
from docling.datamodel.base_models import InputFormat; \
from docling.document_converter import PdfFormatOption; \
opts = PdfPipelineOptions(do_table_structure=True, do_ocr=False); \
DocumentConverter(format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=opts)}); \
print('Docling models cached successfully')"; \
    else \
      python -c "\
from docling.document_converter import DocumentConverter; \
from docling.datamodel.pipeline_options import PdfPipelineOptions; \
from docling.datamodel.base_models import InputFormat; \
from docling.document_converter import PdfFormatOption; \
opts = PdfPipelineOptions(do_table_structure=True, do_ocr=False); \
DocumentConverter(format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=opts)}); \
print('Docling models cached successfully')" 2>&1 || echo "WARN: Docling warmup skipped (non-fatal)"; \
    fi

# Create non-root user for Hardened compliance
RUN useradd -m -u 1001 -s /bin/bash pmoves && \
    chown -R pmoves:pmoves /app

USER pmoves

EXPOSE 8000

CMD ["python", "-m", "app.main"]
