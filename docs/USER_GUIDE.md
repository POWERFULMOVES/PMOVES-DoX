# PMOVES-DoX User Guide

Welcome to PMOVES-DoX - a powerful document intelligence platform for extracting, analyzing, and structuring data from multiple document formats.

## Table of Contents

1. [What is PMOVES-DoX?](#what-is-pmoves-dox)
2. [Quick Start](#quick-start)
3. [Core Concepts](#core-concepts)
4. [Features Overview](#features-overview)
5. [Workflows](#workflows)
6. [Best Practices](#best-practices)
7. [Troubleshooting](#troubleshooting)

---

## What is PMOVES-DoX?

PMOVES-DoX is an enterprise-grade document processing platform that:

- **Extracts** structured data from PDFs, spreadsheets, logs, and APIs
- **Analyzes** documents using AI/ML models (NER, financial detection, metrics)
- **Structures** data with constellation harvest regularization (CHR)
- **Visualizes** insights with interactive dashboards
- **Integrates** with Microsoft Copilot via POML export

### Key Features

✨ **Multi-Format Ingestion**
- PDFs (with table extraction, OCR, VLM descriptions)
- CSV/XLSX spreadsheets
- XML logs with custom XPath mapping
- OpenAPI/Postman API specifications
- Web pages (with headless rendering)
- Audio/video transcription
- Image OCR

🔍 **Advanced Analysis**
- Named Entity Recognition (NER)
- Financial statement detection
- Business metric extraction
- Document structure analysis
- Tag extraction with LangExtract

🎯 **Smart Search**
- Vector-based semantic search (FAISS)
- Type filtering (PDF, API, LOG, TAG)
- Citation-based Q&A with source tracking

📊 **Data Structuring**
- Constellation Harvest Regularization (CHR)
- PCA visualization
- datavzrd dashboard generation

---

## Quick Start

### Installation

#### Option 1: Docker (Recommended)

```bash
# Clone the repository
git clone https://github.com/POWERFULMOVES/PMOVES-DoX.git
cd PMOVES-DoX

# Start with Docker Compose
docker compose up --build

# Access the application
# Frontend: http://localhost:3737
# Backend API: http://localhost:8484
```

#### Option 2: Local Development

**Backend:**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Create .env file
cp .env.example .env
# Edit .env with your settings

# Run backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8484
```

**Frontend:**
```bash
cd frontend
npm install

# Create .env.local
cp .env.local.example .env.local

# Run frontend
npm run dev
```

### First Steps

1. **Upload a Document**
   - Click "Choose Files" or drag & drop
   - Supported: PDF, CSV, XLSX, XML, JSON
   - Wait for processing to complete

2. **Explore Facts**
   - View extracted facts in the Facts panel
   - Click page numbers to see evidence
   - Filter by artifact or search

3. **Run Semantic Search**
   - Use the global search bar
   - Try: "What is the total revenue?"
   - Filter by type (PDF, API, LOG, TAG)

4. **Ask Questions**
   - Navigate to Q&A tab
   - Enter natural language questions
   - Get answers with citations

---

## Core Concepts

### Artifacts
**What:** An artifact is any ingested document or data source.

**Types:**
- `.pdf` - PDF documents
- `.csv`, `.xlsx` - Spreadsheets
- `.xml` - Log files
- `.json` - OpenAPI/Postman specs
- `url` - Web pages

**Attributes:**
- `id` - Unique identifier
- `filename` - Original filename
- `filepath` - Storage location
- `filetype` - File extension
- `report_week` - Optional temporal grouping
- `status` - Processing status

### Facts
**What:** Atomic pieces of information extracted from artifacts.

**Structure:**
```json
{
  "id": "uuid",
  "artifact_id": "uuid",
  "page_number": 1,
  "content": "Revenue: $1.2M",
  "confidence": 0.95,
  "report_week": "2024-W01"
}
```

### Evidence
**What:** Detailed context supporting facts (tables, charts, formulas).

**Types:**
- `table` - Tabular data with headers
- `chart` - Visual charts/figures
- `formula` - Mathematical expressions
- `web_page` - Web content
- `audio_transcript` - Speech-to-text
- `image_ocr` - OCR results

**Structure:**
```json
{
  "id": "uuid",
  "artifact_id": "uuid",
  "content_type": "table",
  "locator": "Page 5, Table 2",
  "preview": "Revenue breakdown...",
  "full_data": { /* complete data */ }
}
```

### Tags
**What:** Semantic labels extracted using LangExtract/LLMs.

**Use Cases:**
- Learning Management System (LMS) tag extraction
- Application governance tagging
- Custom taxonomy mapping

---

## Features Overview

### 1. PDF Processing (Docling)

PMOVES-DoX uses **IBM Docling** for advanced PDF processing:

**Capabilities:**
- Multi-page table detection and merging
- Chart/figure extraction with OCR
- Formula detection (inline + block equations)
- VLM captions for images (optional)
- Layout analysis with heading hierarchy

**Configuration:**
```bash
# Enable VLM picture descriptions
export DOCLING_VLM_REPO=ibm-granite/granite-docling-258M

# GPU acceleration
export DOCLING_DEVICE=cuda

# Financial statement detection
export PDF_FINANCIAL_ANALYSIS=true
```

**Example:**
```bash
# Upload a financial report
curl -X POST http://localhost:8484/upload \
  -F "files=@financial_report_Q4.pdf" \
  -F "report_week=2024-W52"
```

**Output:**
- Extracted tables with merged headers
- Detected financial statements (income, balance sheet, cash flow)
- Chart images saved to `artifacts/charts/`
- Formulas as evidence entries

---

### 2. CSV/XLSX Ingestion

**Smart Processing:**
- Automatic header detection
- Metric extraction (revenue, clicks, impressions)
- CTR calculation for ad performance
- Row-level fact creation

**Example CSV:**
```csv
date,revenue,clicks,impressions
2024-01-01,1500,245,12000
2024-01-02,1820,298,14500
```

**API Call:**
```bash
curl -X POST http://localhost:8484/upload \
  -F "files=@performance_data.csv" \
  -F "report_week=2024-W01"
```

**Extracted Facts:**
- Each row becomes a fact
- Metrics: `revenue=1500`, `clicks=245`, `ctr=2.04%`
- Searchable and queryable

---

### 3. XML Log Ingestion

**Custom XPath Mapping:**

Define how to parse XML logs with custom field mappings:

```bash
# Inline mapping
export XML_XPATH_MAP='{"entry":"//log","fields":{"ts":"./timestamp","level":"./severity","code":"./errorCode","component":"./service","message":"./msg"}}'

# Or file-based
export XML_XPATH_MAP_FILE=/app/config/xpath_map.yaml
```

**Example XML:**
```xml
<logs>
  <log>
    <timestamp>2024-01-01T10:00:00Z</timestamp>
    <severity>ERROR</severity>
    <errorCode>E1001</errorCode>
    <service>payment-service</service>
    <msg>Payment gateway timeout</msg>
  </log>
</logs>
```

**Upload:**
```bash
curl -X POST http://localhost:8484/ingest/xml \
  -H "Content-Type: application/json" \
  -d '{"filepath":"logs/app.xml"}'
```

**Features:**
- Time range filtering
- Severity level filtering
- Error code search
- CSV export

---

### 4. API Catalog (OpenAPI/Postman)

**Ingest API Specifications:**

```bash
# OpenAPI
curl -X POST http://localhost:8484/ingest/openapi \
  -H "Content-Type: application/json" \
  -d '{"filepath":"specs/petstore.json"}'

# Postman Collection
curl -X POST http://localhost:8484/ingest/postman \
  -H "Content-Type: application/json" \
  -d '{"collection_path":"collections/api-tests.json"}'
```

**Catalog View:**
- Browse all API endpoints
- See request/response schemas
- Filter by method (GET, POST, PUT, DELETE)
- Export to documentation

---

### 5. Semantic Search

**Vector Search with FAISS:**

```bash
# Search all content
curl -X POST http://localhost:8484/search \
  -H "Content-Type: application/json" \
  -d '{"q":"total revenue in Q4","k":10}'

# Filter by type
curl -X POST http://localhost:8484/search \
  -H "Content-Type: application/json" \
  -d '{"q":"error handling","types":["api"],"k":5}'
```

**Type Filters:**
- `pdf` - PDF documents only
- `api` - API endpoints only
- `log` - Log entries only
- `tag` - LMS tags only

**Response:**
```json
{
  "results": [
    {
      "content": "Q4 Revenue: $1.2M",
      "score": 0.89,
      "artifact_id": "uuid",
      "page": 12,
      "type": "pdf"
    }
  ]
}
```

---

### 6. Question Answering (Q&A)

**Ask Natural Language Questions:**

```bash
curl -X POST "http://localhost:8484/ask?question=What%20is%20the%20total%20revenue?"
```

**Features:**
- Citation tracking (shows source page/table)
- Confidence scoring
- Multiple answer candidates
- Optional HRM refinement

**UI Workflow:**
1. Navigate to Q&A tab
2. Type question: "What was the highest expense category?"
3. Get answer with citations
4. Click citation to see source evidence

---

### 7. Tag Extraction (LangExtract)

**Extract Semantic Tags:**

**Providers:**
- Google Gemini (default): `gemini-2.5-flash`
- Ollama (local): `ollama:gemma3`

**Configuration:**
```bash
# Use Gemini
export LANGEXTRACT_API_KEY=your-gemini-key
export LANGEXTRACT_MODEL=gemini-2.5-flash

# Or use Ollama
export LANGEXTRACT_PROVIDER=ollama
export LANGEXTRACT_MODEL=ollama:gemma3
export OLLAMA_BASE_URL=http://ollama:11434
```

**API Call:**
```bash
curl -X POST http://localhost:8484/extract/tags \
  -H "Content-Type: application/json" \
  -d '{
    "document_id":"uuid",
    "preset":"lms_comprehensive",
    "dry_run":false,
    "use_hrm":true
  }'
```

**Presets:**
- `lms_comprehensive` - Full LMS taxonomy
- `lms_skills` - Skills/competencies only
- `lms_governance` - Compliance/governance tags
- `custom` - Provide your own prompt

**HRM (Hierarchical Refinement Module):**
- Iterative tag deduplication
- Confidence-based filtering
- Early halting when stable

---

### 8. Data Structuring (CHR)

**Constellation Harvest Regularization:**

Transform unstructured text into structured clusters:

```bash
curl -X POST http://localhost:8484/structure/chr \
  -H "Content-Type: application/json" \
  -d '{
    "artifact_id":"uuid",
    "K":6,
    "units_mode":"sentences",
    "cluster_params":{"min_samples":2}
  }'
```

**Parameters:**
- `K` - Number of clusters
- `units_mode` - `sentences` or `paragraphs`
- `cluster_params` - HDBSCAN parameters

**Output:**
- `chr_clusters.csv` - Clustered data
- `chr_relation_strength.csv` - Similarity matrix
- `chr_pca.png` - PCA visualization
- `datavzrd.yaml` - Dashboard config

**View Results:**
```bash
# Generate datavzrd dashboard
curl -X POST http://localhost:8484/viz/datavzrd \
  -H "Content-Type: application/json" \
  -d '{"csv_path":"artifacts/chr_clusters.csv"}'

# Start datavzrd (with tools profile)
docker compose --profile tools up datavzrd

# Access: http://localhost:5173
```

---

### 9. Summarization

**Generate Multi-Document Summaries:**

**Styles:**
- `bullet` - Bullet point summary
- `executive` - Executive summary paragraph
- `action_items` - Action items list

**Scopes:**
- `workspace` - All artifacts
- `artifact` - Specific artifact(s)

```bash
# Workspace summary
curl -X POST http://localhost:8484/summaries/generate \
  -H "Content-Type: application/json" \
  -d '{"style":"executive","scope":"workspace"}'

# Artifact-specific summary
curl -X POST http://localhost:8484/summaries/generate \
  -H "Content-Type: application/json" \
  -d '{
    "style":"bullet",
    "scope":"artifact",
    "artifact_ids":["uuid1","uuid2"]
  }'
```

**View History:**
```bash
curl "http://localhost:8484/summaries?scope=workspace&style=executive"
```

---

### 10. POML Export (Microsoft Copilot)

**Generate POML for Copilot Studio:**

```bash
curl -X POST http://localhost:8484/export/poml \
  -H "Content-Type: application/json" \
  -d '{
    "document_id":"uuid",
    "title":"Q4 Financial Analysis",
    "variant":"catalog"
  }'
```

**Variants:**
- `generic` - General knowledge base
- `troubleshoot` - Troubleshooting guide
- `catalog` - API/service catalog

**Output:**
```xml
<?xml version="1.0" encoding="UTF-8"?>
<promptOML xmlns="http://schemas.microsoft.com/copilot/promptOML/1.0">
  <title>Q4 Financial Analysis</title>
  <content>
    <section name="Overview">
      <text>Financial data from Q4 2024...</text>
    </section>
    <section name="APIs">
      <text>GET /api/revenue - Returns revenue data</text>
    </section>
  </content>
</promptOML>
```

---

## Workflows

### Workflow 1: Financial Report Analysis

**Goal:** Extract and analyze financial statements from PDF reports.

**Steps:**

1. **Upload PDF:**
   ```bash
   curl -X POST http://localhost:8484/upload \
     -F "files=@annual_report_2024.pdf" \
     -F "report_week=2024-W52"
   ```

2. **Check Financial Detection:**
   ```bash
   curl http://localhost:8484/analysis/financials
   ```

   **Response:**
   ```json
   {
     "statements": [
       {
         "type": "income_statement",
         "page": 15,
         "confidence": 0.92,
         "table_id": "uuid"
       }
     ]
   }
   ```

3. **View Extracted Tables:**
   ```bash
   curl http://localhost:8484/artifacts/{artifact_id}
   ```

4. **Ask Questions:**
   ```bash
   curl -X POST "http://localhost:8484/ask?question=What%20was%20net%20income%20in%202024?"
   ```

5. **Export to POML:**
   ```bash
   curl -X POST http://localhost:8484/export/poml \
     -d '{"document_id":"uuid","variant":"catalog"}'
   ```

---

### Workflow 2: Log Analysis

**Goal:** Analyze application logs for errors and patterns.

**Steps:**

1. **Configure XPath Mapping:**
   ```bash
   export XML_XPATH_MAP='{"entry":"//log","fields":{"ts":"./time","level":"./level","code":"./code","message":"./msg"}}'
   ```

2. **Ingest Logs:**
   ```bash
   curl -X POST http://localhost:8484/ingest/xml \
     -d '{"filepath":"logs/app-2024-01.xml"}'
   ```

3. **Filter Errors:**
   ```bash
   curl "http://localhost:8484/logs?level=ERROR&from=2024-01-01T00:00:00Z&to=2024-01-31T23:59:59Z"
   ```

4. **Export CSV:**
   ```bash
   curl "http://localhost:8484/logs/export?level=ERROR" > errors.csv
   ```

5. **Generate Dashboard:**
   ```bash
   curl -X POST http://localhost:8484/viz/datavzrd/logs \
     -d '{"level":"ERROR","from":"2024-01-01T00:00:00Z"}'
   ```

---

### Workflow 3: API Documentation

**Goal:** Create searchable API catalog from OpenAPI specs.

**Steps:**

1. **Ingest OpenAPI Spec:**
   ```bash
   curl -X POST http://localhost:8484/ingest/openapi \
     -d '{"filepath":"specs/petstore-v3.json"}'
   ```

2. **Browse Endpoints:**
   ```bash
   curl http://localhost:8484/apis
   ```

3. **Search Specific Operation:**
   ```bash
   curl -X POST http://localhost:8484/search \
     -d '{"q":"create user","types":["api"]}'
   ```

4. **View Endpoint Details:**
   ```bash
   curl http://localhost:8484/apis/{api_id}
   ```

5. **Export Documentation:**
   ```bash
   curl -X POST http://localhost:8484/export/poml \
     -d '{"document_id":"uuid","variant":"catalog","title":"API Reference"}'
   ```

---

### Workflow 4: Content Structuring

**Goal:** Organize unstructured documents into thematic clusters.

**Steps:**

1. **Upload Multiple PDFs:**
   ```bash
   for file in docs/*.pdf; do
     curl -X POST http://localhost:8484/upload -F "files=@$file"
   done
   ```

2. **Rebuild Search Index:**
   ```bash
   curl -X POST http://localhost:8484/search/rebuild
   ```

3. **Run CHR:**
   ```bash
   curl -X POST http://localhost:8484/structure/chr \
     -d '{"artifact_id":"uuid","K":8,"units_mode":"paragraphs"}'
   ```

4. **Visualize Clusters:**
   - Open `artifacts/chr_pca.png`
   - Review `artifacts/chr_clusters.csv`

5. **Generate Dashboard:**
   ```bash
   docker compose --profile tools up datavzrd
   # Visit http://localhost:5173
   ```

---

## Best Practices

### Performance

1. **Use GPU Acceleration:**
   ```bash
   export DOCLING_DEVICE=cuda
   export SEARCH_DEVICE=cuda
   ```

2. **Async PDF Processing:**
   ```bash
   curl -X POST "http://localhost:8484/upload?async_pdf=true" -F "files=@large.pdf"
   ```

3. **Batch Uploads:**
   ```bash
   curl -X POST http://localhost:8484/upload \
     -F "files=@doc1.pdf" \
     -F "files=@doc2.pdf" \
     -F "files=@doc3.pdf"
   ```

### Data Organization

1. **Use Report Weeks:**
   ```bash
   # Group by time period
   curl -X POST http://localhost:8484/upload \
     -F "files=@q1_report.pdf" \
     -F "report_week=2024-W13"
   ```

2. **Tag Early:**
   - Extract tags immediately after upload
   - Use dry-run mode to preview
   - Save custom prompts for reuse

3. **Regular Index Rebuilds:**
   ```bash
   # After bulk uploads
   curl -X POST http://localhost:8484/search/rebuild
   ```

### Security

1. **File Size Limits:**
   - Default: 100MB per file
   - Adjust via `MAX_FILE_SIZE` in code

2. **SSRF Protection:**
   - Web ingestion blocks private IPs
   - Only http/https/data URLs allowed

3. **API Authentication:**
   - Currently no auth (local use)
   - Add reverse proxy for production (nginx, Caddy)

### Monitoring

1. **Check Health:**
   ```bash
   curl http://localhost:8484/health
   ```

2. **View Tasks:**
   ```bash
   curl http://localhost:8484/tasks
   ```

3. **Monitor Logs:**
   ```bash
   docker compose logs -f backend
   ```

---

## Troubleshooting

### Common Issues

**1. "Port already in use"**

```bash
# Check what's using the port
lsof -i :8484

# Change port
export PORT=8585
```

**2. "CUDA out of memory"**

```bash
# Use CPU instead
export DOCLING_DEVICE=cpu
export SEARCH_DEVICE=cpu

# Or reduce batch size
export DOCLING_NUM_THREADS=2
```

**3. "Module not found: docling"**

```bash
# Reinstall dependencies
pip install -r backend/requirements.txt --force-reinstall
```

**4. "VLM model not found"**

```bash
# Download model
export HUGGINGFACE_HUB_TOKEN=your-token
export DOCLING_VLM_REPO=ibm-granite/granite-docling-258M

# Or disable VLM
unset DOCLING_VLM_REPO
```

**5. "Search returns no results"**

```bash
# Rebuild index
curl -X POST http://localhost:8484/search/rebuild

# Check if artifacts exist
curl http://localhost:8484/artifacts
```

**6. "LangExtract timeout"**

```bash
# Increase timeout or switch to local Ollama
export LANGEXTRACT_PROVIDER=ollama
export LANGEXTRACT_MODEL=ollama:gemma3
export OLLAMA_BASE_URL=http://localhost:11434
```

### Debug Mode

```bash
# Enable verbose logging
export LOG_LEVEL=DEBUG

# Run backend with reload
uvicorn app.main:app --reload --host 0.0.0.0 --port 8484
```

### Reset Database

```bash
# Clear all data
curl -X DELETE http://localhost:8484/reset

# Or manually
rm backend/database.db
rm -rf backend/uploads/* backend/artifacts/*
```

---

## Next Steps

- 📖 Check out [COOKBOOKS.md](./COOKBOOKS.md) for detailed tutorials
- 🎨 See [DEMOS.md](./DEMOS.md) for interactive examples
- 🔧 Read [API_REFERENCE.md](./API_REFERENCE.md) for complete API docs
- 🏗️ Review [ARCHITECTURE.md](../PROJECT_STRUCTURE.md) for system design

---

**Questions or Issues?**
- GitHub Issues: https://github.com/POWERFULMOVES/PMOVES-DoX/issues
- Documentation: https://github.com/POWERFULMOVES/PMOVES-DoX/tree/main/docs
