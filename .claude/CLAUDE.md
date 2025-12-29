# PMOVES-DoX Developer Context

> Claude Code context file for PMOVES-DoX document intelligence system

## Project Overview

PMOVES-DoX is a document intelligence system providing:
- **PDF Processing**: IBM Docling-powered extraction with layout preservation
- **Vector Search**: FAISS/sentence-transformers semantic search
- **Q&A Interface**: Document-aware question answering
- **API Catalog**: OpenAPI specification management
- **Structured Logging**: Queryable log entries with component tracking

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Frontend (Next.js)                      │
│  Port 3001 (standalone) / 8092 (docked via gateway)         │
├─────────────────────────────────────────────────────────────┤
│                      Backend (FastAPI)                       │
│  Port 8000 (standalone) / 8092 (docked via gateway)         │
├─────────────────────────────────────────────────────────────┤
│  Storage Layer                                               │
│  ├── SQLite + FAISS (standalone)                            │
│  └── Supabase + Qdrant (docked)                             │
└─────────────────────────────────────────────────────────────┘
```

## Operational Modes

### Standalone Mode
- **Database**: SQLite (`backend/db.sqlite3`)
- **Vector Store**: FAISS in-memory with NumPy fallback
- **Ports**: Backend 8000, Frontend 3001
- **Use Case**: Local development, single-user deployment

### Docked Mode (PMOVES.AI Integration)
- **Database**: Supabase PostgreSQL with pgvector
- **Vector Store**: Qdrant
- **Ports**: Proxied through gateway on 8092
- **Message Bus**: NATS for inter-service communication
- **Use Case**: Multi-tenant, production deployment

## Key Files

### Backend
| File | Purpose |
|------|---------|
| `backend/app/main.py` | FastAPI app, routes, CORS config |
| `backend/app/database.py` | SQLite database implementation |
| `backend/app/database_factory.py` | DB backend selection (SQLite/Supabase) |
| `backend/app/database_supabase.py` | Supabase database implementation |
| `backend/app/search.py` | SearchIndex class, FAISS/NumPy vector search |
| `backend/app/analysis.py` | PDF analysis, CHR/Q&A endpoints |
| `backend/app/docling_processor.py` | IBM Docling PDF extraction |
| `backend/app/models.py` | Pydantic request/response models |

### Frontend
| File | Purpose |
|------|---------|
| `frontend/app/page.tsx` | Main dashboard layout |
| `frontend/components/QAInterface.tsx` | Document Q&A chat UI |
| `frontend/components/GlobalSearch.tsx` | Semantic search interface |
| `frontend/components/FileUpload.tsx` | PDF upload with progress |
| `frontend/components/ArtifactsPanel.tsx` | Document list/management |
| `frontend/components/CHRPanel.tsx` | Compact Human Readable view |

### Configuration
| File | Purpose |
|------|---------|
| `docker-compose.yml` | CPU standalone deployment |
| `docker-compose.gpu.yml` | GPU-accelerated deployment |
| `docker-compose.supabase.yml` | Supabase integration |
| `docker-compose.docked.yml` | PMOVES.AI docked mode |
| `backend/.env.example` | Backend environment template |
| `frontend/.env.local.example` | Frontend environment template |

## API Endpoints

### Documents
```bash
# Upload PDF
curl -X POST http://localhost:8000/upload -F "file=@document.pdf"

# List artifacts
curl http://localhost:8000/artifacts

# Get artifact details
curl http://localhost:8000/artifacts/{id}

# Delete artifact
curl -X DELETE http://localhost:8000/artifacts/{id}
```

### Search & Q&A
```bash
# Semantic search
curl "http://localhost:8000/search?q=your+query&k=10"

# Rebuild search index
curl -X POST http://localhost:8000/search/rebuild

# Q&A query
curl -X POST http://localhost:8000/qa \
  -H "Content-Type: application/json" \
  -d '{"question": "What is the main topic?"}'
```

### CHR (Compact Human Readable)
```bash
# Generate CHR for document
curl -X POST http://localhost:8000/chr/{artifact_id}

# Get CHR status
curl http://localhost:8000/chr/{artifact_id}/status
```

### Logs & Tags
```bash
# List logs
curl "http://localhost:8000/logs?level=ERROR&limit=50"

# Create log entry
curl -X POST http://localhost:8000/logs \
  -H "Content-Type: application/json" \
  -d '{"level": "INFO", "message": "Test log", "component": "test"}'

# List tags
curl http://localhost:8000/tags

# Create tag
curl -X POST http://localhost:8000/tags \
  -H "Content-Type: application/json" \
  -d '{"tag": "important", "document_id": "uuid-here"}'
```

## Environment Variables

### Database Selection
| Variable | Description | Default |
|----------|-------------|---------|
| `DB_BACKEND` | Backend type: `sqlite` or `supabase` | `sqlite` |
| `SUPABASE_DUAL_WRITE` | Write to both SQLite and Supabase | `false` |

### Supabase (when DB_BACKEND=supabase)
| Variable | Description |
|----------|-------------|
| `SUPABASE_URL` | Supabase project URL |
| `SUPABASE_ANON_KEY` | Supabase anonymous key |
| `SUPABASE_SERVICE_KEY` | Supabase service role key |
| `SUPABASE_SCHEMA` | Schema name (default: `public`) |

### LLM Configuration
| Variable | Description | Default |
|----------|-------------|---------|
| `LANGEXTRACT_MODEL` | LangExtract model ID | `gemini-2.5-flash` |
| `LANGEXTRACT_API_KEY` | API key for cloud models | - |
| `LANGEXTRACT_PROVIDER` | Provider (blank or `ollama`) | - |
| `OLLAMA_BASE_URL` | Ollama server URL | `http://ollama:11434` |

### Search & Embeddings
| Variable | Description | Default |
|----------|-------------|---------|
| `SEARCH_MODEL` | Sentence transformer model | `all-MiniLM-L6-v2` |
| `SEARCH_DEVICE` | Compute device (cpu/cuda) | auto-detect |

### Docling (PDF Processing)
| Variable | Description | Default |
|----------|-------------|---------|
| `DOCLING_VLM_REPO` | VLM model for image description | - |
| `DOCLING_DEVICE` | Accelerator (auto/cuda/cpu) | `auto` |
| `DOCLING_NUM_THREADS` | Thread limit | - |
| `HUGGINGFACE_HUB_TOKEN` | HuggingFace token | - |

### Watch Folder
| Variable | Description | Default |
|----------|-------------|---------|
| `WATCH_ENABLED` | Enable folder watching | `true` |
| `WATCH_DIR` | Directory to watch | `/app/watch` |
| `WATCH_DEBOUNCE_MS` | Debounce interval | `1000` |

### Server
| Variable | Description | Default |
|----------|-------------|---------|
| `PORT` | Backend port | `8000` |
| `FRONTEND_ORIGIN` | CORS allowed origin | `http://localhost:3000` |

## Development Commands

### Local Development
```bash
# Backend (requires Python 3.11+)
cd backend
cp .env.example .env
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Frontend (requires Node 18+)
cd frontend
cp .env.local.example .env.local
npm install
npm run dev
```

### Docker
```bash
# Standalone CPU
docker-compose up -d

# Standalone GPU
docker-compose -f docker-compose.gpu.yml up -d

# With Supabase
docker-compose -f docker-compose.supabase.yml up -d

# Docked mode (PMOVES.AI)
docker-compose -f docker-compose.docked.yml up -d
```

### Testing
```bash
# Backend tests
cd backend
pytest -v

# Frontend tests
cd frontend
npm test
```

## Common Patterns

### Adding a New Endpoint
1. Define Pydantic models in `backend/app/models.py`
2. Add route handler in `backend/app/main.py`
3. Add database methods in `backend/app/database.py` if needed
4. For Supabase support, also update `backend/app/database_supabase.py`
5. Update OpenAPI docs with proper tags

### Adding a Frontend Component
1. Create component in `frontend/components/`
2. Use existing patterns from similar components
3. Connect to backend via fetch/axios
4. Add to appropriate page layout

### Database Backend Selection
The database backend is controlled by `DB_BACKEND` env var:
- `sqlite` (default): Uses `backend/db.sqlite3`
- `supabase`: Uses Supabase PostgreSQL
- Set `SUPABASE_DUAL_WRITE=true` to write to both

## Troubleshooting

### Search Returns Empty
1. Check if index is built: `GET /search/status`
2. Rebuild index: `POST /search/rebuild`
3. Verify documents exist: `GET /artifacts`

### PDF Processing Fails
1. Check Docling installation: `python -c "import docling"`
2. Verify PDF is not corrupted
3. Check disk space for artifacts directory

### CORS Errors
1. Verify `FRONTEND_ORIGIN` includes your frontend URL
2. Check browser console for specific blocked origin
3. Ensure backend is running on expected port

### Docked Mode Connection Issues
1. Verify Supabase credentials
2. Check NATS connectivity
3. Ensure gateway is routing correctly

## Code Style

- **Python**: Black formatter, type hints, docstrings
- **TypeScript**: Prettier, strict mode, functional components
- **Commits**: Conventional commits (`feat:`, `fix:`, `docs:`)
- **PRs**: Require review, pass CI, squash merge

## Related Resources

- [PMOVES.AI Main Repo](https://github.com/POWERFULMOVES/PMOVES.AI)
- [IBM Docling Docs](https://ds4sd.github.io/docling/)
- [FAISS Wiki](https://github.com/facebookresearch/faiss/wiki)
- [Supabase Docs](https://supabase.com/docs)
