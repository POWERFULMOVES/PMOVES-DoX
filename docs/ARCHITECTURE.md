# PMOVES-DoX Architecture

Technical architecture and system design documentation.

## Table of Contents

1. [System Overview](#system-overview)
2. [Architecture Diagram](#architecture-diagram)
3. [Backend Architecture](#backend-architecture)
4. [Frontend Architecture](#frontend-architecture)
5. [Data Flow](#data-flow)
6. [Processing Pipeline](#processing-pipeline)
7. [Storage Architecture](#storage-architecture)
8. [Search & Indexing](#search--indexing)
9. [Security Architecture](#security-architecture)
10. [Deployment Models](#deployment-models)

---

## System Overview

PMOVES-DoX is a document intelligence platform built on a modern microservices architecture:

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Browser   │────▶│   Next.js   │────▶│   FastAPI   │
│  (Client)   │     │  Frontend   │     │   Backend   │
└─────────────┘     └─────────────┘     └─────────────┘
                            │                    │
                            │              ┌─────▼─────┐
                            │              │  SQLite   │
                            │              │  Database │
                            │              └───────────┘
                            │                    │
                            │              ┌─────▼─────┐
                            │              │  FAISS    │
                            │              │  Index    │
                            │              └───────────┘
                            │                    │
                            │              ┌─────▼─────┐
                            └─────────────▶│ datavzrd  │
                                           │ (Tools)   │
                                           └───────────┘
```

### Technology Stack

**Backend:**
- FastAPI (Python 3.10+)
- SQLModel/SQLAlchemy (ORM)
- Docling 2.x (PDF processing)
- FAISS (vector search)
- sentence-transformers (embeddings)
- spaCy (NER)
- LangExtract (tag extraction)

**Frontend:**
- Next.js 14 (React 18)
- TypeScript 5.3
- Tailwind CSS 3.4
- Axios (HTTP client)

**Infrastructure:**
- Docker & Docker Compose
- NVIDIA GPU support
- Jetson ARM64 support
- Optional Ollama integration

---

## Architecture Diagram

### High-Level Architecture

```
┌────────────────────────────────────────────────────────────┐
│                        Frontend Layer                       │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐      │
│  │ Upload  │  │ Search  │  │   Q&A   │  │  Viz    │      │
│  │ UI      │  │ UI      │  │   UI    │  │  UI     │      │
│  └────┬────┘  └────┬────┘  └────┬────┘  └────┬────┘      │
└───────┼───────────┼────────────┼────────────┼─────────────┘
        │           │            │            │
        └───────────┴────────────┴────────────┘
                    │
         ┌──────────▼──────────┐
         │   API Gateway       │
         │   (CORS, Routes)    │
         └──────────┬──────────┘
                    │
┌───────────────────▼────────────────────────────────────────┐
│                      Backend Layer                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │ Ingestion   │  │ Analysis    │  │ Search      │        │
│  │ Pipeline    │  │ Engine      │  │ Engine      │        │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘        │
│         │                │                 │                │
│         └────────────────┴─────────────────┘                │
│                          │                                  │
│         ┌────────────────▼────────────────┐                │
│         │    Database Factory             │                │
│         │  ┌────────┐    ┌──────────┐    │                │
│         │  │SQLite  │ or │Supabase  │    │                │
│         │  └────────┘    └──────────┘    │                │
│         └─────────────────────────────────┘                │
└────────────────────────────────────────────────────────────┘
                    │
┌───────────────────▼────────────────────────────────────────┐
│                    Storage Layer                            │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                 │
│  │ Uploads  │  │Artifacts │  │  FAISS   │                 │
│  │ (Files)  │  │ (Output) │  │ (Index)  │                 │
│  └──────────┘  └──────────┘  └──────────┘                 │
└────────────────────────────────────────────────────────────┘
```

---

## Backend Architecture

### FastAPI Application Structure

```python
# app/main.py - Entry point
from fastapi import FastAPI
from app.database_factory import init_database
from app.qa_engine import QAEngine
from app.search import SearchIndex

# Initialize services
db, DB_BACKEND_META = init_database()
qa_engine = QAEngine(db)
search_index = SearchIndex(db)

# Routes are defined as FastAPI endpoints
@app.post("/upload")
async def upload_files(...):
    # File upload logic
    pass

@app.post("/search")
async def search(...):
    # Search logic using FAISS
    pass
```

### Module Organization

```
backend/
├── app/
│   ├── main.py                    # FastAPI app + all endpoints
│   ├── database.py                # SQLite/SQLModel backend
│   ├── database_supabase.py       # Supabase backend
│   ├── database_factory.py        # Backend factory pattern
│   ├── qa_engine.py               # Question answering engine
│   ├── search.py                  # FAISS vector search
│   ├── chr_pipeline.py            # CHR data structuring
│   ├── export_poml.py             # POML generation
│   ├── hrm.py                     # Experimental HRM
│   │
│   ├── ingestion/                 # Document processors
│   │   ├── pdf_processor.py      # Docling PDF pipeline
│   │   ├── csv_processor.py      # CSV/spreadsheet
│   │   ├── xlsx_processor.py     # Excel processing
│   │   ├── xml_ingestion.py      # XML log parsing
│   │   ├── openapi_ingestion.py  # OpenAPI specs
│   │   ├── postman_ingestion.py  # Postman collections
│   │   ├── web_ingestion.py      # Web scraping
│   │   ├── media_transcriber.py  # Audio/video
│   │   └── image_ocr.py          # Image OCR
│   │
│   ├── analysis/                  # Analysis modules
│   │   ├── financial_statement_detector.py
│   │   ├── structure_processor.py
│   │   ├── ner_processor.py
│   │   ├── metric_extractor.py
│   │   └── summarization.py
│   │
│   └── extraction/
│       └── langextract_adapter.py # Tag extraction
│
├── migrations/                    # Alembic migrations
├── tests/                         # Unit tests
└── requirements.txt               # Dependencies
```

### Database Schema

```sql
-- Artifacts table
CREATE TABLE artifact (
    id VARCHAR PRIMARY KEY,
    filename VARCHAR NOT NULL,
    filepath VARCHAR NOT NULL,
    filetype VARCHAR NOT NULL,
    report_week VARCHAR,
    status VARCHAR,
    source_url VARCHAR,
    extra_json TEXT  -- JSON extras
);

-- Facts table
CREATE TABLE fact (
    id VARCHAR PRIMARY KEY,
    artifact_id VARCHAR REFERENCES artifact(id),
    page_number INTEGER,
    content TEXT,
    confidence FLOAT,
    report_week VARCHAR
);

-- Evidence table
CREATE TABLE evidence (
    id VARCHAR PRIMARY KEY,
    artifact_id VARCHAR REFERENCES artifact(id),
    content_type VARCHAR,  -- table, chart, formula, etc.
    locator VARCHAR,       -- page/location
    preview TEXT,          -- short preview
    full_data_json TEXT    -- complete JSON data
);

-- Log entries
CREATE TABLE logrow (
    id VARCHAR PRIMARY KEY,
    artifact_id VARCHAR REFERENCES artifact(id),
    ts VARCHAR,            -- timestamp
    level VARCHAR,         -- ERROR, WARN, INFO
    code VARCHAR,          -- error code
    component VARCHAR,     -- service name
    message TEXT
);

-- API operations
CREATE TABLE apirow (
    id VARCHAR PRIMARY KEY,
    artifact_id VARCHAR REFERENCES artifact(id),
    path VARCHAR,
    method VARCHAR,        -- GET, POST, etc.
    operation_id VARCHAR,
    summary TEXT,
    details_json TEXT
);

-- Tags
CREATE TABLE tagrow (
    id VARCHAR PRIMARY KEY,
    artifact_id VARCHAR REFERENCES artifact(id),
    document_id VARCHAR,
    name VARCHAR,
    category VARCHAR,
    confidence FLOAT,
    hrm_steps INTEGER,     -- if HRM used
    hrm_metadata_json TEXT
);

-- Summaries
CREATE TABLE summaryrow (
    id VARCHAR PRIMARY KEY,
    style VARCHAR,         -- bullet, executive, action_items
    scope VARCHAR,         -- workspace, artifact
    scope_json TEXT,       -- details
    summary TEXT,
    created_at VARCHAR
);
```

### Database Factory Pattern

```python
# app/database_factory.py

def init_database():
    """Initialize database backend based on config."""
    backend = os.getenv("DB_BACKEND", "sqlite")

    if backend == "supabase":
        from app.database_supabase import SupabaseDatabase
        db = SupabaseDatabase(...)
        return db, "supabase"

    elif backend == "sqlite":
        from app.database import ExtendedDatabase
        db = ExtendedDatabase("database.db")
        return db, "sqlite"

    # Dual-write mode for migration
    if os.getenv("SUPABASE_DUAL_WRITE") == "true":
        from app.database import ExtendedDatabase
        from app.database_supabase import SupabaseDatabase

        sqlite_db = ExtendedDatabase("database.db")
        supabase_db = SupabaseDatabase(...)

        # Wrapper that writes to both
        class DualWriteDB:
            def add_artifact(self, data):
                sqlite_db.add_artifact(data)
                supabase_db.add_artifact(data)
                return data["id"]
            # ... other methods

        return DualWriteDB(), "dual"
```

---

## Frontend Architecture

### Next.js Structure

```
frontend/
├── app/
│   ├── layout.tsx          # Root layout
│   ├── page.tsx            # Main SPA
│   └── globals.css         # Global styles
│
├── components/             # React components
│   ├── HeaderBar.tsx       # Top navigation
│   ├── GlobalSearch.tsx    # Search bar
│   ├── FileUpload.tsx      # Drag & drop upload
│   ├── QAInterface.tsx     # Q&A tab
│   ├── FactsViewer.tsx     # Facts display
│   ├── TagsPanel.tsx       # Tag extraction UI
│   ├── LogsPanel.tsx       # Logs viewer
│   ├── APIsPanel.tsx       # API catalog
│   ├── ArtifactsPanel.tsx  # Artifact list
│   ├── EntitiesPanel.tsx   # NER results
│   ├── StructurePanel.tsx  # Document structure
│   ├── MetricHitsPanel.tsx # Metrics display
│   ├── SummariesPanel.tsx  # Summaries
│   ├── MediaArtifactsPanel.tsx  # Audio/video/OCR
│   ├── CHRPanel.tsx        # CHR interface
│   ├── SettingsModal.tsx   # Settings
│   └── Toast.tsx           # Notifications
│
├── lib/
│   └── config.ts           # Configuration helpers
│
├── package.json
├── tsconfig.json
├── next.config.js
└── tailwind.config.js
```

### Component Architecture

```typescript
// Main page - Tab-based UI
export default function Home() {
  const [activeTab, setActiveTab] = useState('upload');

  return (
    <div>
      <HeaderBar />
      <TabNavigation activeTab={activeTab} onChange={setActiveTab} />

      {activeTab === 'upload' && <FileUpload />}
      {activeTab === 'facts' && <FactsViewer />}
      {activeTab === 'qa' && <QAInterface />}
      {activeTab === 'tags' && <TagsPanel />}
      {/* ... more tabs */}
    </div>
  );
}

// Component pattern
function FactsViewer() {
  const [facts, setFacts] = useState([]);
  const API = getApiBase();

  useEffect(() => {
    fetch(`${API}/facts`)
      .then(r => r.json())
      .then(data => setFacts(data.facts));
  }, []);

  return (
    <div>
      {facts.map(fact => (
        <FactCard key={fact.id} fact={fact} />
      ))}
    </div>
  );
}
```

---

## Data Flow

### Upload & Processing Flow

```
┌─────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
│ Browser │────▶│ Frontend │────▶│  FastAPI │────▶│   File   │
│         │     │  (Next)  │     │ /upload  │     │  Storage │
└─────────┘     └──────────┘     └─────┬────┘     └──────────┘
                                        │
                              ┌─────────▼─────────┐
                              │ Process by type   │
                              ├───────────────────┤
                              │ PDF → Docling     │
                              │ CSV → pandas      │
                              │ XML → XPath       │
                              │ JSON → OpenAPI    │
                              └─────────┬─────────┘
                                        │
                              ┌─────────▼─────────┐
                              │ Extract Facts &   │
                              │ Evidence          │
                              └─────────┬─────────┘
                                        │
                              ┌─────────▼─────────┐
                              │ Store in Database │
                              └─────────┬─────────┘
                                        │
                              ┌─────────▼─────────┐
                              │ Update FAISS Index│
                              └───────────────────┘
```

### Search Flow

```
┌─────────┐     ┌──────────┐     ┌──────────┐
│  User   │────▶│  Search  │────▶│ Embedding│
│  Query  │     │   API    │     │  Model   │
└─────────┘     └──────────┘     └─────┬────┘
                                        │
                              ┌─────────▼─────────┐
                              │ Query Vector      │
                              │ (384 dimensions)  │
                              └─────────┬─────────┘
                                        │
                              ┌─────────▼─────────┐
                              │ FAISS Search      │
                              │ (cosine similarity)│
                              └─────────┬─────────┘
                                        │
                              ┌─────────▼─────────┐
                              │ Top-K Results     │
                              │ with scores       │
                              └─────────┬─────────┘
                                        │
                              ┌─────────▼─────────┐
                              │ Filter by type    │
                              │ (if specified)    │
                              └─────────┬─────────┘
                                        │
                              ┌─────────▼─────────┐
                              │ Return to Client  │
                              └───────────────────┘
```

### Q&A Flow

```
┌─────────┐     ┌──────────┐     ┌──────────┐
│Question │────▶│ Q&A API  │────▶│  Search  │
│         │     │          │     │  Facts   │
└─────────┘     └──────────┘     └─────┬────┘
                                        │
                              ┌─────────▼─────────┐
                              │ Top-10 Candidates │
                              └─────────┬─────────┘
                                        │
                              ┌─────────▼─────────┐
                              │ Rank by Relevance │
                              └─────────┬─────────┘
                                        │
                              ┌─────────▼─────────┐
                              │ Extract Answer    │
                              │ (simple string    │
                              │  matching/summary)│
                              └─────────┬─────────┘
                                        │
                              ┌─────────▼─────────┐
                              │ Optional: HRM     │
                              │ Refinement        │
                              └─────────┬─────────┘
                                        │
                              ┌─────────▼─────────┐
                              │ Return Answer +   │
                              │ Citations         │
                              └───────────────────┘
```

---

## Processing Pipeline

### PDF Processing (Docling)

```
┌─────────────┐
│ PDF Upload  │
└──────┬──────┘
       │
       ▼
┌─────────────────────┐
│ Docling Converter   │
│ - Layout Analysis   │
│ - OCR (if needed)   │
│ - Table Detection   │
│ - Chart Extraction  │
└──────┬──────────────┘
       │
       ├──────────┬──────────┬─────────┐
       ▼          ▼          ▼         ▼
┌──────────┐ ┌────────┐ ┌────────┐ ┌────────┐
│  Tables  │ │ Charts │ │ Formulas│ │  Text  │
└─────┬────┘ └────┬───┘ └────┬───┘ └────┬───┘
      │           │          │          │
      │   ┌───────▼──────────▼──────────▼────┐
      │   │ Merge Multi-Page Tables          │
      │   └──────────────┬───────────────────┘
      │                  │
      ▼                  ▼
┌──────────────────────────────────────┐
│ Financial Statement Detection        │
│ - Income Statement (revenue/expense) │
│ - Balance Sheet (assets/liabilities) │
│ - Cash Flow (operating/investing)    │
└──────────────┬───────────────────────┘
               │
               ▼
┌──────────────────────────────────────┐
│ Store as Evidence                    │
│ - Tables → full_data JSON            │
│ - Charts → image + caption           │
│ - Formulas → LaTeX representation    │
└──────────────────────────────────────┘
```

### CSV/XLSX Processing

```
┌─────────────┐
│ CSV Upload  │
└──────┬──────┘
       │
       ▼
┌─────────────────────┐
│ pandas.read_csv()   │
│ - Detect headers    │
│ - Infer types       │
└──────┬──────────────┘
       │
       ▼
┌─────────────────────┐
│ Metric Extraction   │
│ - revenue, clicks   │
│ - impressions       │
│ - CTR calculation   │
└──────┬──────────────┘
       │
       ▼
┌─────────────────────┐
│ Create Facts        │
│ - 1 fact per row    │
│ - Include metrics   │
└──────┬──────────────┘
       │
       ▼
┌─────────────────────┐
│ Store in Database   │
└─────────────────────┘
```

### XML Log Processing

```
┌─────────────┐
│ XML Upload  │
└──────┬──────┘
       │
       ▼
┌─────────────────────┐
│ Apply XPath Mapping │
│ - entry path        │
│ - field mappings    │
└──────┬──────────────┘
       │
       ▼
┌─────────────────────┐
│ Parse Each Entry    │
│ - timestamp         │
│ - level (severity)  │
│ - code (error code) │
│ - component         │
│ - message           │
└──────┬──────────────┘
       │
       ▼
┌─────────────────────┐
│ Store as LogRow     │
│ - Indexed by level  │
│ - Queryable fields  │
└─────────────────────┘
```

---

## Storage Architecture

### File System Layout

```
PMOVES-DoX/
├── backend/
│   ├── database.db              # SQLite database
│   │
│   ├── uploads/                 # Uploaded files
│   │   ├── uuid1_document.pdf
│   │   ├── uuid2_data.csv
│   │   └── uuid3_logs.xml
│   │
│   ├── artifacts/               # Processed outputs
│   │   ├── charts/              # Extracted charts
│   │   │   ├── uuid1_chart1.png
│   │   │   └── uuid1_chart2.png
│   │   │
│   │   ├── web/                 # Web page artifacts
│   │   │   ├── uuid_web.html
│   │   │   ├── uuid_web.txt
│   │   │   └── uuid_web.metadata.json
│   │   │
│   │   ├── chr_clusters.csv     # CHR output
│   │   ├── chr_pca.png          # PCA visualization
│   │   ├── datavzrd.yaml        # Dashboard config
│   │   │
│   │   └── poml/                # POML exports
│   │       └── uuid.poml
│   │
│   └── .faiss_index/            # FAISS index files
│       ├── index.bin
│       └── metadata.json
```

### FAISS Index Structure

```python
# app/search.py

class SearchIndex:
    def __init__(self, db):
        self.db = db
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        self.index = None  # FAISS index
        self.fact_ids = [] # Corresponding fact IDs

    def rebuild(self):
        """Rebuild index from all facts."""
        facts = self.db.get_facts()

        # Generate embeddings
        texts = [f['content'] for f in facts]
        embeddings = self.model.encode(texts)  # (N, 384)

        # Create FAISS index
        dimension = 384
        self.index = faiss.IndexFlatL2(dimension)
        self.index.add(embeddings.astype('float32'))

        # Store mapping
        self.fact_ids = [f['id'] for f in facts]

    def search(self, query, k=10):
        """Search for top-k similar facts."""
        # Embed query
        query_vec = self.model.encode([query])

        # Search FAISS
        distances, indices = self.index.search(
            query_vec.astype('float32'),
            k
        )

        # Map back to facts
        results = []
        for dist, idx in zip(distances[0], indices[0]):
            fact_id = self.fact_ids[idx]
            fact = self.db.get_fact(fact_id)
            results.append({
                'fact': fact,
                'score': 1 / (1 + dist),  # Convert distance to similarity
                'distance': dist
            })

        return results
```

---

## Search & Indexing

### Embedding Model

```
Model: all-MiniLM-L6-v2
Dimensions: 384
Provider: sentence-transformers
Max sequence: 256 tokens

Why this model?
- Fast (CPU-friendly)
- Multilingual support
- Good balance of quality/performance
- Small model size (~80MB)
```

### Index Management

```python
# Lifecycle
1. Initial build: On first search request
2. Incremental updates: After each upload
3. Full rebuild: Manual trigger via /search/rebuild

# Storage
- In-memory during runtime
- Persisted to disk (optional)
- Rebuilt from database on restart
```

### Search Optimization

```python
# 1. GPU Acceleration (optional)
if torch.cuda.is_available():
    model = model.to('cuda')
    index = faiss.index_cpu_to_gpu(resource, 0, index)

# 2. Approximate Search (for large datasets)
# Use HNSW or IVF instead of FlatL2
index = faiss.IndexHNSWFlat(dimension, 32)
index.hnsw.efConstruction = 40
index.hnsw.efSearch = 16

# 3. Dimensionality Reduction
# Use PCA to reduce from 384 → 128 dimensions
pca = faiss.PCAMatrix(384, 128)
index = faiss.IndexPreTransform(pca, faiss.IndexFlatL2(128))
```

---

## Security Architecture

### Current Security Model

**Authentication:** None (local use)
**Authorization:** None
**Data Access:** Full read/write

### Security Features Implemented

1. **Path Traversal Protection**
```python
# Sanitize filenames
safe_filename = os.path.basename(file.filename)
safe_filename = safe_filename.replace("/", "_").replace("\\", "_")
```

2. **SSRF Protection**
```python
# Block private IPs
ip = ipaddress.ip_address(hostname)
if ip.is_private or ip.is_loopback:
    raise ValueError("Access denied")
```

3. **File Size Limits**
```python
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB
if len(file_content) > MAX_FILE_SIZE:
    raise HTTPException(413, "File too large")
```

4. **CORS Restrictions**
```python
# Only allow configured origins
allow_origins = [os.getenv("FRONTEND_ORIGIN")]
```

### Production Security Recommendations

```
1. Add Authentication
   - Use OAuth2/JWT
   - Implement API keys
   - Add rate limiting

2. Network Security
   - Deploy behind VPN
   - Use reverse proxy (nginx)
   - Enable HTTPS/TLS

3. Data Security
   - Encrypt database
   - Encrypt uploaded files
   - Implement audit logging

4. Access Control
   - Role-based permissions
   - Document-level access control
   - Multi-tenancy support
```

---

## Deployment Models

### Development (Local)

```bash
# Backend
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8484

# Frontend
cd frontend
npm install
npm run dev
```

### Docker Compose (CPU)

```yaml
# docker-compose.cpu.yml
services:
  backend:
    build: ./backend
    ports:
      - "8484:8484"
    volumes:
      - ./backend/uploads:/app/uploads
      - ./backend/artifacts:/app/artifacts

  frontend:
    build: ./frontend
    ports:
      - "3737:3737"
    depends_on:
      - backend
```

### Docker Compose (GPU)

```yaml
# docker-compose.yml
services:
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile.gpu
    ports:
      - "8484:8484"
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]
```

### Kubernetes (Production)

```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: pmoves-dox-backend
spec:
  replicas: 3
  selector:
    matchLabels:
      app: pmoves-dox-backend
  template:
    metadata:
      labels:
        app: pmoves-dox-backend
    spec:
      containers:
      - name: backend
        image: pmoves-dox:latest
        ports:
        - containerPort: 8484
        env:
        - name: DB_BACKEND
          value: "supabase"
        resources:
          limits:
            nvidia.com/gpu: 1
```

### Cloud Deployment (AWS)

```
Architecture:
- ECS Fargate (backend containers)
- S3 (file storage)
- RDS PostgreSQL (database)
- CloudFront (frontend)
- API Gateway (rate limiting)
- Cognito (authentication)

Benefits:
- Auto-scaling
- Managed services
- High availability
- Global CDN
```

---

## Performance Considerations

### Bottlenecks

1. **PDF Processing**
   - Docling is CPU/GPU intensive
   - Large PDFs take minutes
   - Solution: Async processing, queue

2. **FAISS Search**
   - Linear search O(N)
   - Solution: Use HNSW approximation

3. **Database Queries**
   - SQLite limitations for concurrent writes
   - Solution: Migrate to PostgreSQL/Supabase

### Optimization Strategies

```python
# 1. Caching
from functools import lru_cache

@lru_cache(maxsize=100)
def get_artifact(artifact_id):
    return db.get_artifact(artifact_id)

# 2. Pagination
@app.get("/facts")
def get_facts(offset: int = 0, limit: int = 100):
    return db.get_facts(offset, limit)

# 3. Background Tasks
from fastapi import BackgroundTasks

@app.post("/upload")
async def upload(file, background_tasks: BackgroundTasks):
    background_tasks.add_task(process_pdf, file)
    return {"status": "queued"}

# 4. Connection Pooling
from sqlalchemy.pool import QueuePool

engine = create_engine(
    "sqlite:///database.db",
    poolclass=QueuePool,
    pool_size=10
)
```

---

## Monitoring & Observability

### Metrics Endpoint

```http
GET /metrics
```

Returns Prometheus-formatted metrics:
```
# HELP pmoves_requests_total Total requests
# TYPE pmoves_requests_total counter
pmoves_requests_total{endpoint="/upload",status="200"} 42
pmoves_requests_total{endpoint="/search",status="200"} 158

# HELP pmoves_processing_time_seconds Processing time
# TYPE pmoves_processing_time_seconds histogram
pmoves_processing_time_seconds_bucket{le="1.0"} 45
pmoves_processing_time_seconds_bucket{le="5.0"} 89
```

### Logging

```python
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.post("/upload")
async def upload(...):
    logger.info(f"Upload started: {file.filename}")
    # Process file
    logger.info(f"Upload completed: {artifact_id}")
```

### Health Checks

```python
@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "database": "connected" if db.test_connection() else "error",
        "faiss": "loaded" if search_index.index else "not_loaded"
    }
```

---

## Next Steps

- 📖 Review [USER_GUIDE.md](./USER_GUIDE.md) for usage
- 🍳 Try [COOKBOOKS.md](./COOKBOOKS.md) for examples
- 🔧 Check [API_REFERENCE.md](./API_REFERENCE.md) for API docs

**Questions?** Open an issue on GitHub!
