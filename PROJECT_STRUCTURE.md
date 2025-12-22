# Project Structure Overview

```
PMOVES-DoX/
├── README.md                           # Main documentation
├── ADVANCED_FEATURES_PLAN.md          # Roadmap for advanced features
├── setup.ps1                          # Windows setup script
├── .gitignore                         # Git ignore rules
│
├── backend/                           # FastAPI Backend (Port 8000)
│   ├── requirements.txt               # Python dependencies
│   ├── .env.example                   # Environment variables template
│   │
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                    # FastAPI application entry point
│   │   ├── database.py                # In-memory database (upgrade to SQLite/Postgres)
│   │   ├── qa_engine.py               # Question answering logic
│   │   │
│   │   └── ingestion/                 # Document processors
│   │       ├── __init__.py
│   │       ├── pdf_processor.py       # PDF with IBM Granite Docling
│   │       ├── csv_processor.py       # CSV processing
│   │       └── xlsx_processor.py      # Excel processing
│   │
│   ├── uploads/                       # Uploaded files storage
│   │   └── .gitkeep
│   ├── artifacts/                     # Processed outputs (MD, JSON)
│   │   └── .gitkeep
│   ├── docs/                          # Documentation (API, Architecture, Math UI)
│   └── tests/                         # Unit tests
│       └── .gitkeep
│
├── external/                          # Submodules and external tools
│   └── Pmoves-hyperdimensions/        # Mathematical Visualization Engine
├── external_services/                 # Docker services (DB, Weaviate, etc.)
├── frontend/                          # Next.js Frontend (Port 3000)
├── GEMINI.md                          # Geometric Intelligence Agent Guide
├── PROJECT_STRUCTURE.md               # This file
    ├── package.json                   # Node dependencies
    ├── tsconfig.json                  # TypeScript configuration
    ├── next.config.js                 # Next.js configuration
    ├── tailwind.config.js             # Tailwind CSS configuration
    ├── postcss.config.js              # PostCSS configuration
    │
    ├── app/
    │   ├── layout.tsx                 # Root layout with metadata
    │   ├── page.tsx                   # Main application page
    │   └── globals.css                # Global styles
    │
    └── components/
        ├── FileUpload.tsx             # File upload component
        ├── QAInterface.tsx            # Question & Answer interface
        └── FactsViewer.tsx            # Extracted facts display
```

## Technology Stack

### Backend
- **Framework**: FastAPI 0.109
- **PDF Processing**: Docling 1.16.2 (IBM Granite model)
- **Data Processing**: Pandas, OpenPyXL
- **Database**: In-memory (ready for SQLite/PostgreSQL)
- **Vector Store**: Supabase integration ready

### Frontend
- **Framework**: Next.js 14 with TypeScript
- **Styling**: Tailwind CSS
- **HTTP Client**: Axios
- **UI**: React with TypeScript

## Quick Start

### Option 1: Automated Setup (Windows)
```powershell
.\setup.ps1
```

### Option 2: Manual Setup

**Backend:**
```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m app.main
```

**Frontend:**
```powershell
cd frontend
npm install
npm run dev
```

## Key Features

✅ **Multi-Format Processing**
   - PDF (with IBM Granite Docling for advanced layout analysis)
   - CSV
   - XLSX/XLS

✅ **Automatic Fact Extraction**
   - Revenue, Spend, Conversions
   - CPA, ROAS, CTR calculations
   - Bounding box coordinates

✅ **Q&A with Citations**
   - Ask natural language questions
   - Get answers with source references
   - Page and location tracking

✅ **Modern UI**
   - File upload with drag-and-drop
   - Real-time processing status
   - Citation viewer with location info

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Health check |
| `/upload` | POST | Upload and process documents |
| `/facts` | GET | Get all extracted facts |
| `/evidence/{id}` | GET | Get specific evidence |
| `/ask` | POST | Ask a question |
| `/reset` | DELETE | Clear all data |

## Data Flow

1. **Upload** → User uploads PDF/CSV/XLSX
2. **Process** → Docling extracts structure, tables, text
3. **Extract** → Facts and metrics identified
4. **Store** → Facts saved with evidence pointers
5. **Query** → User asks questions
6. **Retrieve** → Relevant facts retrieved
7. **Cite** → Answer generated with citations

## Advanced Features (See ADVANCED_FEATURES_PLAN.md)

- Multi-page table detection
- Chart/graph extraction
- Financial statement parsing
- Named entity recognition
- Vector store integration (Supabase)
- Semantic search
- Multi-hop reasoning
- Citation highlighting in PDFs

## Ecosystem Integration (PMOVES-BoTZ)

This repository (`PMOVES-DoX`) functions as the specialized "Document Intelligence" module within the larger PMOVES ecosystem.

### Branch Strategy
*   **`main`**: The active development branch for new features (like Geometric Intelligence).
*   **`hardened-DoX`**: The production-ready branch utilized by **PMOVES-BoTZ**.
    *   Requests from BoTZ to DoX running on this branch are treated as "mini super capable helpers".
    *   Enhanced by **n8n** workflows for orchestration.

### Submodules & Integrations
*   `external/n8n`: Integration with **n8n** for advanced workflows (Cookbooks).
*   `external/conductor`: PMOVES-BoTZ context and CLI extensions.

