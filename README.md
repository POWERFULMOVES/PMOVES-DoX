# Meeting Analyst App

An intelligent document analysis system that processes PDFs, CSVs, and Excel files to extract metrics and answer questions with citations.

## Features

- **Multi-format Document Processing**: PDF (using IBM Granite Docling), CSV, XLSX
- **Automatic Fact Extraction**: Extracts metrics like ROAS, CPA, CTR, revenue, spend
- **Q&A with Citations**: Ask questions and get answers with source references
- **Location Tracking**: Tracks exact page and bounding box coordinates for PDF content
- **FastAPI Backend**: High-performance async API
- **React/Next.js Frontend**: Modern, responsive UI

## Technology Stack

### Backend
- FastAPI
- Docling (IBM Granite model for PDF processing)
- Pandas for data analysis
- Python 3.10+

### Frontend
- Next.js 14
- TypeScript
- Tailwind CSS
- Axios

## Setup Instructions (Windows/PowerShell)

### Backend Setup

```powershell
# Navigate to backend directory
cd meeting-analyst-app/backend

# Copy env template (optional)
copy .env.example .env

# (Optional) Add Hugging Face token for model downloads
# In .env, set HUGGINGFACE_HUB_TOKEN=your_token (or HF_API_KEY)
# Optionally enable VLM picture descriptions:
# DOCLING_VLM_REPO=ibm-granite/granite-docling-258m-demo

# Create virtual environment
python -m venv venv

# Activate virtual environment
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Run the backend (PORT via .env if set)
python -m app.main
```

Backend will run on `http://localhost:8000`

### Frontend Setup

```powershell
# Navigate to frontend directory
cd meeting-analyst-app/frontend

# Copy env template (optional)
copy .env.local.example .env.local

# Install dependencies
npm install

# Run development server
npm run dev
```

Frontend will run on `http://localhost:3000`

## Docker Compose (GPU default)

Prereqs: Docker Desktop installed and running.

```powershell
cd meeting-analyst-app
# Optional (recommended on Docker Desktop):
docker compose --compatibility up --build
```

- Backend (GPU): http://localhost:8000 (CORS allows http://localhost:3000 by default)
- Frontend: http://localhost:3000 (talks to backend at http://localhost:8000)
- datavzrd dashboard (if a viz has been generated): http://localhost:5173
 - schemavzrd schema docs (if DB_URL is set): http://localhost:5174

Data folders `backend/uploads` and `backend/artifacts` are volume-mounted.
There is also a watch folder: `meeting-analyst-app/watch` mounted to `/app/watch` in the backend.

PDF OCR support in container: the backend image installs `poppler-utils`, `tesseract-ocr`, and `tesseract-ocr-eng` to support Docling’s PDF parsing and OCR.

Hugging Face auth in Compose:
- Set an environment variable on your host named `HF_API_KEY` or `HUGGINGFACE_HUB_TOKEN` before running compose, e.g. in PowerShell:
  - `$env:HF_API_KEY = 'hf_xxx_your_token'`
  - `docker compose up --build`
- To enable Granite Docling picture descriptions, set on host:
  - `$env:DOCLING_VLM_REPO = 'ibm-granite/granite-docling-258M'` (or `'ibm-granite/granite-docling-258m-demo'`)

Notes on model downloads:
- The first run will download model weights into a cached volume (`hf-cache`). This can take a few minutes depending on bandwidth.
- Backend image includes CPU-only PyTorch; no GPU is required for the 258M model.

### CPU-only mode
If you don’t want to use the GPU image, run the CPU override:

```powershell
docker compose -f docker-compose.cpu.yml up --build
```

### GPU acceleration (NVIDIA)
If you have an NVIDIA GPU and the NVIDIA Container Toolkit installed, you can run the default CUDA-enabled backend image for faster PDF + VLM processing.

1) Set environment variables (PowerShell example):

```
$env:HF_API_KEY = 'hf_xxx_your_token'
$env:DOCLING_VLM_REPO = 'ibm-granite/granite-docling-258M'
```

2) Start (GPU is default in docker-compose.yml):

```
cd meeting-analyst-app
docker compose --compatibility up --build
```

This uses `backend/Dockerfile.gpu` based on `pytorch/pytorch:2.3.1-cuda12.1-cudnn8-runtime` and requests a GPU from Docker Desktop.

Troubleshooting:
- Make sure the NVIDIA drivers and Container Toolkit are installed. Run `nvidia-smi` on the host, and `docker run --gpus all nvidia/cuda:12.1.1-runtime-ubuntu22.04 nvidia-smi` to confirm GPU is available in containers.
- If the container cannot access the GPU, ensure Docker Desktop settings have GPU support enabled and the NVIDIA toolkit is installed.

## Usage

1. **Upload Documents**: Drag and drop or select PDF, CSV, or XLSX files
2. **Automatic Processing**: Files are automatically analyzed and facts extracted
3. **Ask Questions**: Type questions like "what is the total ROAS?" or "show me revenue"
4. **View Citations**: See exactly where each fact came from with page numbers and coordinates

### Sample files
- CSV: `meeting-analyst-app/samples/sample.csv`
- PDF: `meeting-analyst-app/samples/sample.pdf` (downloaded by `setup.ps1`; or use any PDF you have)

### Watch Folder

Drop `.pdf`, `.csv`, `.xlsx`, or `.xls` files into `meeting-analyst-app/watch` and the backend will auto‑ingest them. Behavior is controlled by env vars (see `backend/.env.example`):

- `WATCH_ENABLED` (default `true`)
- `WATCH_DIR` (default `/app/watch` in the container)
- `WATCH_DEBOUNCE_MS` (default `1000`) — wait for file size to stabilize
- `WATCH_MIN_BYTES` (default `1`) — minimum size to consider a file ready

Watcher status: `GET /watch`

## API Endpoints

- `POST /upload` - Upload and process documents
- `GET /facts` - Retrieve all extracted facts
- `GET /evidence/{id}` - Get specific evidence by ID
- `POST /ask` - Ask a question and get answer with citations
- `DELETE /reset` - Clear all data
- `POST /extract/langextract` - Run Google LangExtract over an artifact or raw text (returns structured entities + HTML visualization path)
- `POST /convert` - Convert processed artifact to txt or docx
- `GET /download?rel=...` - Download artifacts (whitelisted under `artifacts/`)
- `POST /structure/chr` - Run Constellation Harvest Regularization over an artifact (PDF/CSV/XLSX)
  - Body: `{ artifact_id, K?, iters?, bins?, beta?, seed?, units_mode? ('paragraphs'|'sentences'), include_tables? }`
  - Returns: `mhep`, `Hg`, `Hs`, `preview_rows`, and artifact paths (CSV/JSON/plot)
- `POST /viz/datavzrd` - Materialize a datavzrd project for the artifact’s CHR CSV
- `GET /artifacts` - List uploaded artifacts (ids, filenames)
- `GET /documents` - List ingested documents (pdf/xml/openapi/postman)
- `GET /tasks` and `GET /tasks/{id}` - Background task summaries + status
- `GET /config` - Runtime config (VLM repo, HF auth, GPU availability)
- `GET /health` - Uptime status

## Local LLMs (Ollama)

This compose spins up an Ollama service by default (port 11434) to support local models for LangExtract.

Use local Gemma 3 (LLM) and Gemma Embedding:

```powershell
docker exec -it ollama bash -lc "ollama pull gemma3 && ollama pull gemma-embedding"
```

Configure backend to use Ollama:

- In `backend/.env`:
  - `LANGEXTRACT_PROVIDER=ollama`
  - `LANGEXTRACT_MODEL=ollama:gemma3`
  - `OLLAMA_BASE_URL=http://ollama:11434`

Now `POST /extract/langextract` will run extraction against the local Gemma 3 model.

Notes:
- You can also pull Qwen models via Ollama if available (e.g., `ollama pull qwen2.5`).
- For HF-only local runners (vLLM/TGI), we can add another service on request; Ollama covers most local use-cases with minimal setup.

## Project Structure

```
meeting-analyst-app/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI application
│   │   ├── database.py          # In-memory database
│   │   ├── qa_engine.py         # Question answering logic
│   │   └── ingestion/
│   │       ├── pdf_processor.py  # PDF processing with Docling
│   │       ├── csv_processor.py  # CSV processing
│   │       └── xlsx_processor.py # Excel processing
│   ├── uploads/                  # Uploaded files
│   ├── artifacts/                # Processed outputs (MD, JSON)
│   └── requirements.txt
└── frontend/
    ├── app/
    │   └── page.tsx             # Main page
    ├── components/
    │   ├── FileUpload.tsx       # File upload component
    │   ├── QAInterface.tsx      # Q&A interface
    │   └── FactsViewer.tsx      # Facts display
    └── package.json
```

## Next Steps

See `ADVANCED_FEATURES_PLAN.md` for roadmap of advanced PDF processing features.

## Smoke Tests

Quickly verify the backend endpoints end-to-end with the included smoke script.

Prereqs: Python 3.10+ on your host.

```powershell
# With the stack running (Docker or local), in a new terminal:
cd meeting-analyst-app
python -m venv venv
./venv/Scripts/Activate.ps1
pip install -r smoke/requirements.txt

# Optionally set a custom API base (default http://localhost:8000)
$env:API_BASE = 'http://localhost:8000'

python smoke/smoke_backend.py
```

What it does:
- Checks `/health`
- Uploads `samples/sample.csv`
- Confirms facts were extracted
- Runs CHR on the new artifact and downloads the CSV
- Converts the artifact to TXT and downloads it
- Generates a datavzrd project
- Ingests XML/OpenAPI/Postman samples and queries `/logs` and `/apis`

Exit code 0 indicates success; otherwise the script prints an error and returns non‑zero.
### High-fidelity DOCX via Pandoc

The backend images include `pandoc`. Conversion from markdown (Docling output) to DOCX/TXT uses pandoc when available for best fidelity and falls back to a minimal python-docx mapping otherwise.
### datavzrd Dashboard Service

This repo includes a datavzrd service that builds the latest `viz.yaml` under `artifacts/datavzrd/**/viz.yaml` (from the CHR panel’s “Generate datavzrd project”) and serves the generated static dashboard at http://localhost:5173.

- The service image builds from source (`cargo install datavzrd`) — the first build can take a few minutes.
- By default it picks the newest viz.yaml. To force a specific one, set `VIZ_FILE` in the service to the absolute path, e.g. `VIZ_FILE=/app/artifacts/datavzrd/<stem>/viz.yaml` (edit `docker-compose.yml`).
- You can regenerate dashboards by clicking “Generate datavzrd project” again and refreshing the datavzrd page.

#### Spells (datavzrd-spells)

You can enrich dashboards with prebuilt spells from https://github.com/datavzrd/datavzrd-spells. The current service builds and serves dashboards from `viz.yaml`. To use spells:

- Add spell configs to your `viz.yaml` (see the spells repo for examples).
- If a spell requires local assets, mount them under `backend/artifacts/datavzrd/<stem>/` and reference them relative in `viz.yaml`.

### schemavzrd (DB Schema Docs)

The compose file includes a `schemavzrd` service (http://localhost:5174). Set `DB_URL` in your environment before starting compose, for example:

```powershell
$env:DB_URL = 'postgresql://user:pass@host:5432/dbname'
docker compose up --build schemavzrd
```

The service writes outputs to `backend/artifacts/out/schema` and serves them.

### Mangle (data transformation)

To include https://github.com/google/mangle in your workflow, run it alongside the stack (outside of Compose), and output transformed CSVs into `backend/artifacts` or `watch/`. A minimal pattern:

```powershell
# Install Go and mangle on your host, or build a container separately
go install github.com/google/mangle/cmd/mangle@latest

# Transform a CSV and drop into watch folder for auto-ingest
mangle run your.mangle -i path\to\input.csv -o meeting-analyst-app\watch\transformed.csv
```

You can also add a custom container for mangle later if you prefer containerized transforms.

## Database Migrations (Alembic)

SQLite is used by default (`db.sqlite3`). Alembic scaffolding is included:

```powershell
cd meeting-analyst-app/backend
alembic upgrade head           # apply migrations (none initially)
alembic revision --autogenerate -m "init"  # create a new migration from current SQLModel metadata
alembic upgrade head
```
