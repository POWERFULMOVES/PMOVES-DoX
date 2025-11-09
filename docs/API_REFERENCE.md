# PMOVES-DoX API Reference

Complete REST API documentation for PMOVES-DoX backend.

## Base URL

```
http://localhost:8484
```

## Table of Contents

1. [Core Endpoints](#core-endpoints)
2. [Document Management](#document-management)
3. [Ingestion](#ingestion)
4. [Search & Query](#search--query)
5. [Analysis](#analysis)
6. [Tag Extraction](#tag-extraction)
7. [Data Processing](#data-processing)
8. [Visualization](#visualization)
9. [Export](#export)
10. [Task Management](#task-management)
11. [Error Codes](#error-codes)

---

## Core Endpoints

### Health Check

```http
GET /
GET /health
```

Check if the API is running.

**Response:**
```json
{
  "status": "ok",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

---

### Get Configuration

```http
GET /config
```

Get runtime configuration.

**Response:**
```json
{
  "gpu_available": true,
  "ollama_available": true,
  "vlm_enabled": true,
  "hrm_enabled": false,
  "db_backend": "sqlite"
}
```

---

## Document Management

### Upload Files

```http
POST /upload
```

Upload documents for processing.

**Content-Type:** `multipart/form-data`

**Parameters:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `files` | file[] | Yes | Files to upload (PDF, CSV, XLSX, XML, etc.) |
| `report_week` | string | No | ISO week (e.g., "2024-W01") for grouping |
| `async_pdf` | boolean | No | Process PDFs asynchronously (default: false) |
| `urls` | string[] | No | Web URLs to ingest |

**Example:**
```bash
curl -X POST http://localhost:8484/upload \
  -F "files=@document.pdf" \
  -F "files=@data.csv" \
  -F "report_week=2024-W20"
```

**Response:**
```json
{
  "results": [
    {
      "filename": "document.pdf",
      "status": "success",
      "facts_count": 42,
      "evidence_count": 15,
      "artifact_id": "uuid"
    }
  ]
}
```

**Error Response (413):**
```json
{
  "detail": "File size exceeds maximum allowed size of 100MB"
}
```

---

### List Artifacts

```http
GET /artifacts
```

Get all uploaded artifacts.

**Parameters:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `report_week` | string | No | Filter by report week |

**Response:**
```json
{
  "artifacts": [
    {
      "id": "uuid",
      "filename": "report.pdf",
      "filepath": "/app/uploads/uuid_report.pdf",
      "filetype": ".pdf",
      "report_week": "2024-W20",
      "status": "processed",
      "facts_count": 42,
      "table_evidence": 8,
      "chart_evidence": 3,
      "formula_evidence": 12
    }
  ]
}
```

---

### Get Artifact Details

```http
GET /artifacts/{artifact_id}
```

Get detailed information about a specific artifact.

**Path Parameters:**
| Field | Type | Description |
|-------|------|-------------|
| `artifact_id` | string | UUID of the artifact |

**Response:**
```json
{
  "id": "uuid",
  "filename": "report.pdf",
  "facts": [...],
  "evidence": [...],
  "table_evidence": 8,
  "chart_evidence": 3
}
```

---

### Get Media Artifacts

```http
GET /artifacts/media
```

Get artifacts from audio, video, image OCR, and web pages.

**Response:**
```json
{
  "artifacts": [
    {
      "id": "uuid",
      "filename": "interview.mp3",
      "filetype": ".mp3",
      "transcript": "...",
      "duration": 1800
    }
  ]
}
```

---

### List Documents

```http
GET /documents
```

Get all ingested documents.

**Response:**
```json
{
  "documents": [
    {
      "id": "uuid",
      "filename": "report.pdf",
      "artifact_id": "uuid",
      "facts_count": 42
    }
  ]
}
```

---

### Load Sample Data

```http
POST /load_samples
```

Load sample files for testing.

**Response:**
```json
{
  "loaded": [
    "sample.csv",
    "sample.xml",
    "sample_openapi.json"
  ]
}
```

---

## Ingestion

### Ingest XML Logs

```http
POST /ingest/xml
```

Ingest XML log files with custom XPath mapping.

**Content-Type:** `application/json`

**Request Body:**
```json
{
  "filepath": "logs/app.xml",
  "xpath_map": {
    "entry": "//log",
    "fields": {
      "ts": "./timestamp",
      "level": "./severity",
      "code": "./errorCode",
      "component": "./service",
      "message": "./message"
    }
  }
}
```

**Response:**
```json
{
  "logs_processed": 1523,
  "artifact_id": "uuid"
}
```

---

### Ingest OpenAPI Spec

```http
POST /ingest/openapi
```

Ingest OpenAPI/Swagger specification.

**Request Body:**
```json
{
  "filepath": "specs/api-v3.json"
}
```

**Response:**
```json
{
  "operations_processed": 45,
  "artifact_id": "uuid"
}
```

---

### Ingest Postman Collection

```http
POST /ingest/postman
```

Ingest Postman collection.

**Request Body:**
```json
{
  "collection_path": "collections/api-tests.json"
}
```

**Response:**
```json
{
  "requests_processed": 32,
  "artifact_id": "uuid"
}
```

---

## Search & Query

### Semantic Search

```http
POST /search
```

Perform vector-based semantic search.

**Content-Type:** `application/json`

**Request Body:**
```json
{
  "q": "total revenue in Q4",
  "k": 10,
  "types": ["pdf", "api", "log", "tag"]
}
```

**Parameters:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `q` | string | Yes | Search query |
| `k` | integer | No | Number of results (default: 10) |
| `types` | string[] | No | Filter by type (pdf, api, log, tag) |

**Response:**
```json
{
  "results": [
    {
      "content": "Q4 Revenue: $1.2M",
      "score": 0.89,
      "artifact_id": "uuid",
      "page": 12,
      "type": "pdf",
      "evidence_id": "uuid"
    }
  ],
  "query": "total revenue in Q4",
  "took_ms": 45
}
```

---

### Rebuild Search Index

```http
POST /search/rebuild
```

Rebuild the vector search index.

**Response:**
```json
{
  "status": "rebuilt",
  "indexed_facts": 1523,
  "took_ms": 2340
}
```

---

### Question Answering

```http
POST /ask
```

Ask natural language questions.

**Query Parameters:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `question` | string | Yes | Question to ask |
| `use_hrm` | boolean | No | Use HRM refinement (default: false) |

**Example:**
```bash
curl -X POST "http://localhost:8484/ask?question=What%20is%20the%20total%20revenue?"
```

**Response:**
```json
{
  "answer": "Total revenue was $5.8 million",
  "confidence": 0.92,
  "citations": [
    {
      "artifact_id": "uuid",
      "page": 5,
      "content": "Q1 Revenue: $1.2M"
    }
  ],
  "hrm_steps": 3
}
```

---

### Get Logs

```http
GET /logs
```

Get log entries with filtering.

**Query Parameters:**
| Field | Type | Description |
|-------|------|-------------|
| `level` | string | Filter by level (ERROR, WARN, INFO, DEBUG) |
| `from` | string | ISO 8601 timestamp |
| `to` | string | ISO 8601 timestamp |
| `component` | string | Filter by component |
| `code` | string | Filter by error code |

**Example:**
```bash
curl "http://localhost:8484/logs?level=ERROR&from=2024-01-01T00:00:00Z"
```

**Response:**
```json
{
  "logs": [
    {
      "ts": "2024-01-15T10:30:00Z",
      "level": "ERROR",
      "code": "E1001",
      "component": "payment-service",
      "message": "Payment gateway timeout"
    }
  ]
}
```

---

### Export Logs to CSV

```http
GET /logs/export
```

Export logs as CSV.

**Query Parameters:** Same as `/logs`

**Response:** CSV file

```csv
ts,level,code,component,message
2024-01-15T10:30:00Z,ERROR,E1001,payment-service,Payment gateway timeout
```

---

### Get APIs

```http
GET /apis
```

Get all API operations from OpenAPI/Postman.

**Response:**
```json
{
  "apis": [
    {
      "id": "uuid",
      "path": "/users",
      "method": "POST",
      "operation_id": "createUser",
      "summary": "Create a new user",
      "tags": ["users"]
    }
  ]
}
```

---

### Get API Details

```http
GET /apis/{api_id}
```

Get detailed API operation information.

**Response:**
```json
{
  "path": "/users",
  "method": "POST",
  "operation_id": "createUser",
  "summary": "Create a new user",
  "parameters": [...],
  "responses": {...}
}
```

---

## Analysis

### Get Facts

```http
GET /facts
```

Get all extracted facts.

**Query Parameters:**
| Field | Type | Description |
|-------|------|-------------|
| `report_week` | string | Filter by report week |
| `artifact_id` | string | Filter by artifact |

**Response:**
```json
{
  "facts": [
    {
      "id": "uuid",
      "artifact_id": "uuid",
      "page_number": 5,
      "content": "Revenue: $1.2M",
      "confidence": 0.95,
      "report_week": "2024-W01"
    }
  ]
}
```

---

### Get Evidence

```http
GET /evidence/{evidence_id}
```

Get specific evidence details.

**Response:**
```json
{
  "id": "uuid",
  "artifact_id": "uuid",
  "content_type": "table",
  "locator": "Page 5, Table 2",
  "preview": "Revenue breakdown...",
  "full_data": {
    "headers": ["Quarter", "Revenue"],
    "rows": [...]
  }
}
```

---

### Get Named Entities

```http
GET /analysis/entities
```

Get named entities from NER.

**Response:**
```json
{
  "entities": [
    {
      "text": "Microsoft",
      "label": "ORG",
      "count": 12,
      "artifacts": ["uuid1", "uuid2"]
    }
  ]
}
```

---

### Get Document Structure

```http
GET /analysis/structure
```

Get document heading hierarchy.

**Response:**
```json
{
  "headings": [
    {
      "level": 1,
      "text": "Executive Summary",
      "page": 3
    }
  ]
}
```

---

### Get Metric Hits

```http
GET /analysis/metrics
```

Get extracted business metrics.

**Response:**
```json
{
  "metrics": [
    {
      "metric": "revenue",
      "value": "$1.2M",
      "context": "Q1 revenue was $1.2M",
      "page": 5
    }
  ]
}
```

---

### Get Financial Statements

```http
GET /analysis/financials
```

Get detected financial statements.

**Response:**
```json
{
  "statements": [
    {
      "artifact_id": "uuid",
      "type": "income_statement",
      "page": 5,
      "confidence": 0.94,
      "metrics": {
        "revenue": "$1.2M",
        "net_income": "$340K"
      }
    }
  ]
}
```

---

### Get Artifact Analysis

```http
GET /analysis/artifacts/{artifact_id}
```

Get tables, charts, and formulas for an artifact.

**Response:**
```json
{
  "tables": 8,
  "charts": 3,
  "formulas": 12,
  "details": [...]
}
```

---

## Tag Extraction

### Get Tags

```http
GET /tags
```

Get all extracted tags.

**Query Parameters:**
| Field | Type | Description |
|-------|------|-------------|
| `document_id` | string | Filter by document |

**Response:**
```json
{
  "tags": [
    {
      "id": "uuid",
      "document_id": "uuid",
      "name": "Python",
      "category": "Programming Languages",
      "confidence": 0.95
    }
  ]
}
```

---

### Extract Tags

```http
POST /extract/tags
```

Extract tags using LangExtract.

**Request Body:**
```json
{
  "document_id": "uuid",
  "preset": "lms_comprehensive",
  "custom_prompt": "Extract skill tags...",
  "dry_run": false,
  "use_hrm": true,
  "api_key": "optional-override-key"
}
```

**Parameters:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `document_id` | string | Yes | Document UUID |
| `preset` | string | No | Preset name (lms_comprehensive, lms_skills, etc.) |
| `custom_prompt` | string | No | Custom extraction prompt |
| `dry_run` | boolean | No | Preview without saving (default: false) |
| `use_hrm` | boolean | No | Use HRM refinement (default: false) |
| `api_key` | string | No | Override API key |

**Response:**
```json
{
  "tags": [
    {
      "name": "Python",
      "category": "Programming Languages",
      "confidence": 0.95
    }
  ],
  "hrm_steps": 2,
  "dry_run": false
}
```

---

### Auto-Tag

```http
POST /autotag/{artifact_id}
```

Quick auto-tagging with default preset.

**Response:**
```json
{
  "tags": [...],
  "count": 15
}
```

---

### Get Tag Presets

```http
GET /tags/presets
```

Get available LangExtract presets.

**Response:**
```json
{
  "presets": [
    {
      "name": "lms_comprehensive",
      "description": "Full LMS taxonomy"
    },
    {
      "name": "lms_skills",
      "description": "Skills and competencies only"
    }
  ]
}
```

---

### Get/Set Tag Prompt

```http
GET /tags/prompt/{document_id}
POST /tags/prompt/{document_id}
```

Get or save custom tag extraction prompt.

**POST Request Body:**
```json
{
  "prompt": "Extract the following tags..."
}
```

---

## Data Processing

### Run CHR

```http
POST /structure/chr
```

Run Constellation Harvest Regularization.

**Request Body:**
```json
{
  "artifact_id": "uuid",
  "K": 6,
  "units_mode": "sentences",
  "cluster_params": {
    "min_samples": 2,
    "min_cluster_size": 5
  }
}
```

**Parameters:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `artifact_id` | string | Yes | Artifact UUID |
| `K` | integer | Yes | Number of clusters |
| `units_mode` | string | Yes | "sentences" or "paragraphs" |
| `cluster_params` | object | No | HDBSCAN parameters |

**Response:**
```json
{
  "K": 6,
  "units_processed": 234,
  "artifacts": {
    "rel_csv": "artifacts/chr_clusters.csv",
    "pca_plot": "artifacts/chr_pca.png",
    "relation_csv": "artifacts/chr_relation_strength.csv"
  }
}
```

---

### Convert Document

```http
POST /convert
```

Convert artifact to TXT or DOCX.

**Request Body:**
```json
{
  "artifact_id": "uuid",
  "format": "txt"
}
```

**Response:**
```json
{
  "converted_file": "artifacts/document.txt"
}
```

---

### Run LangExtract

```http
POST /extract/langextract
```

Run Google LangExtract on text.

**Request Body:**
```json
{
  "text": "Course content...",
  "prompt": "Extract tags..."
}
```

**Response:**
```json
{
  "extracted": [...]
}
```

---

## Visualization

### Generate datavzrd

```http
POST /viz/datavzrd
```

Generate datavzrd visualization project.

**Request Body:**
```json
{
  "csv_path": "artifacts/chr_clusters.csv",
  "name": "Analysis Dashboard"
}
```

**Response:**
```json
{
  "viz_file": "artifacts/datavzrd.yaml",
  "message": "Start with: docker compose --profile tools up datavzrd"
}
```

---

### Generate Logs Dashboard

```http
POST /viz/datavzrd/logs
```

Generate datavzrd for log analysis.

**Request Body:**
```json
{
  "level": "ERROR",
  "from": "2024-01-01T00:00:00Z",
  "to": "2024-01-31T23:59:59Z"
}
```

---

## Export

### Export POML

```http
POST /export/poml
```

Generate POML for Microsoft Copilot.

**Request Body:**
```json
{
  "document_id": "uuid",
  "title": "Financial Analysis",
  "variant": "catalog"
}
```

**Parameters:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `document_id` | string | Yes | Document UUID |
| `title` | string | No | POML title |
| `variant` | string | No | "generic", "troubleshoot", or "catalog" |

**Response:**
```json
{
  "rel": "artifacts/poml_uuid.poml"
}
```

---

### Download File

```http
GET /download
```

Download artifact files.

**Query Parameters:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `rel` | string | Yes | Relative path to file |

**Example:**
```bash
curl "http://localhost:8484/download?rel=artifacts/chr_clusters.csv" > clusters.csv
```

---

### Open PDF

```http
GET /open/pdf
```

Serve PDF at specific page (requires `OPEN_PDF_ENABLED=true`).

**Query Parameters:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `artifact_id` | string | Yes | Artifact UUID |
| `page` | integer | No | Page number |

**Response:** PDF file stream

---

## Summarization

### Generate Summary

```http
POST /summaries/generate
```

Generate multi-document summary.

**Request Body:**
```json
{
  "style": "executive",
  "scope": "workspace",
  "artifact_ids": ["uuid1", "uuid2"]
}
```

**Parameters:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `style` | string | Yes | "bullet", "executive", or "action_items" |
| `scope` | string | Yes | "workspace" or "artifact" |
| `artifact_ids` | string[] | Conditional | Required if scope="artifact" |

**Response:**
```json
{
  "id": "uuid",
  "style": "executive",
  "scope": "workspace",
  "summary": "The analysis reveals...",
  "created_at": "2024-01-15T10:30:00Z"
}
```

---

### List Summaries

```http
GET /summaries
```

Get summary history.

**Query Parameters:**
| Field | Type | Description |
|-------|------|-------------|
| `scope` | string | Filter by scope |
| `style` | string | Filter by style |

**Response:**
```json
{
  "summaries": [...]
}
```

---

## Task Management

### List Tasks

```http
GET /tasks
```

Get all background tasks.

**Response:**
```json
{
  "tasks": [
    {
      "id": "uuid",
      "status": "processing",
      "filename": "large_report.pdf",
      "progress": 45
    }
  ]
}
```

---

### Get Task Status

```http
GET /tasks/{task_id}
```

Get specific task details.

**Response:**
```json
{
  "id": "uuid",
  "status": "completed",
  "filename": "report.pdf",
  "result": {
    "facts_count": 42,
    "evidence_count": 15
  }
}
```

---

## HRM Experiments

### HRM Echo

```http
POST /experiments/hrm/echo
```

Test HRM text normalization.

**Request Body:**
```json
{
  "text": "  hello   world  "
}
```

**Response:**
```json
{
  "normalized": "hello world",
  "steps": 2
}
```

---

### HRM Sort Digits

```http
POST /experiments/hrm/sort_digits
```

Test HRM digit sorting.

**Request Body:**
```json
{
  "seq": "93241"
}
```

**Response:**
```json
{
  "sorted": "12349",
  "steps": 4
}
```

---

### Get HRM Metrics

```http
GET /metrics/hrm
```

Get HRM performance metrics.

**Response:**
```json
{
  "total_calls": 145,
  "avg_steps": 2.4,
  "avg_time_ms": 123
}
```

---

## System

### Get Metrics

```http
GET /metrics
```

Get system metrics (Prometheus format).

**Response:** Prometheus metrics

```
# HELP pmoves_requests_total Total requests
# TYPE pmoves_requests_total counter
pmoves_requests_total{endpoint="/upload"} 42
```

---

### Reset Database

```http
DELETE /reset
```

⚠️ **WARNING:** Deletes all data!

**Response:**
```json
{
  "status": "reset",
  "deleted": {
    "artifacts": 15,
    "facts": 523,
    "evidence": 187
  }
}
```

---

### Get Watch Folder Status

```http
GET /watch
```

Get auto-ingestion watch folder status.

**Response:**
```json
{
  "enabled": true,
  "path": "/app/watch",
  "files_pending": 3
}
```

---

## Error Codes

### HTTP Status Codes

| Code | Meaning | Description |
|------|---------|-------------|
| 200 | OK | Request successful |
| 201 | Created | Resource created |
| 400 | Bad Request | Invalid request parameters |
| 403 | Forbidden | Access denied (SSRF, disabled feature) |
| 404 | Not Found | Resource not found |
| 413 | Payload Too Large | File exceeds size limit |
| 422 | Unprocessable Entity | Validation error |
| 500 | Internal Server Error | Server error |

### Common Error Responses

**Validation Error (422):**
```json
{
  "detail": [
    {
      "loc": ["body", "artifact_id"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

**SSRF Protection (403):**
```json
{
  "detail": "SSRF protection: Access to localhost is not allowed"
}
```

**File Too Large (413):**
```json
{
  "detail": "File size exceeds maximum allowed size of 100MB"
}
```

---

## Rate Limits

Currently no rate limiting is implemented. For production use, add a reverse proxy with rate limiting (nginx, Caddy).

---

## Authentication

Currently no authentication is required. This is designed for local/internal use. For production:

1. Use reverse proxy with auth (nginx + basic auth)
2. Deploy behind VPN
3. Use API gateway (AWS API Gateway, Kong)

---

## Pagination

Most list endpoints do not currently support pagination. For large datasets:
- Use filtering parameters (report_week, artifact_id)
- Export to CSV and process externally
- Use search with `k` parameter to limit results

---

## Content Types

### Request

- `multipart/form-data` - File uploads
- `application/json` - API calls
- `application/x-www-form-urlencoded` - Form data

### Response

- `application/json` - JSON responses
- `text/csv` - CSV exports
- `application/pdf` - PDF files
- `text/plain` - Prometheus metrics

---

## CORS

Configured via `FRONTEND_ORIGIN` environment variable.

Default: `http://localhost:3737`

---

## Webhooks

Not currently supported. For event notifications, poll `/tasks` endpoint.

---

## SDK / Client Libraries

### Python

```python
import requests

class PMOVESDoxClient:
    def __init__(self, base_url="http://localhost:8484"):
        self.base_url = base_url

    def upload(self, filepath, report_week=None):
        with open(filepath, "rb") as f:
            files = {"files": f}
            data = {"report_week": report_week} if report_week else {}
            resp = requests.post(f"{self.base_url}/upload", files=files, data=data)
            return resp.json()

    def search(self, query, k=10, types=None):
        payload = {"q": query, "k": k}
        if types:
            payload["types"] = types
        resp = requests.post(f"{self.base_url}/search", json=payload)
        return resp.json()

    def ask(self, question, use_hrm=False):
        params = {"question": question, "use_hrm": str(use_hrm).lower()}
        resp = requests.post(f"{self.base_url}/ask", params=params)
        return resp.json()

# Usage
client = PMOVESDoxClient()
result = client.upload("document.pdf", "2024-W20")
answers = client.ask("What is the total revenue?")
```

### JavaScript

```javascript
class PMOVESDoxClient {
  constructor(baseUrl = "http://localhost:8484") {
    this.baseUrl = baseUrl;
  }

  async upload(file, reportWeek = null) {
    const formData = new FormData();
    formData.append("files", file);
    if (reportWeek) formData.append("report_week", reportWeek);

    const resp = await fetch(`${this.baseUrl}/upload`, {
      method: "POST",
      body: formData
    });
    return resp.json();
  }

  async search(query, k = 10, types = null) {
    const payload = { q: query, k };
    if (types) payload.types = types;

    const resp = await fetch(`${this.baseUrl}/search`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    return resp.json();
  }

  async ask(question, useHrm = false) {
    const params = new URLSearchParams({ question, use_hrm: useHrm });
    const resp = await fetch(`${this.baseUrl}/ask?${params}`, {
      method: "POST"
    });
    return resp.json();
  }
}

// Usage
const client = new PMOVESDoxClient();
const result = await client.upload(fileInput.files[0], "2024-W20");
const answer = await client.ask("What is the total revenue?");
```

---

## Next Steps

- 📖 Read [USER_GUIDE.md](./USER_GUIDE.md) for feature tutorials
- 🍳 Follow [COOKBOOKS.md](./COOKBOOKS.md) for recipes
- 🎨 See [DEMOS.md](./DEMOS.md) for examples

**Questions?** Open an issue on GitHub!
