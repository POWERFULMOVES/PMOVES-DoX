# Data Flow Diagrams

This document describes the key data flows within PMOVES-DoX, including document ingestion, search, agent coordination, and knowledge retrieval.

## Overview

PMOVES-DoX processes multiple types of input through various pipelines:

```mermaid
graph TB
    subgraph Inputs
        PDF[PDF Documents]
        CSV[CSV/Excel Files]
        API[API Specs]
        WEB[Web URLs]
        IMG[Images]
    end

    subgraph Processing
        INGEST[Ingestion Pipeline]
        EXTRACT[Extraction Engine]
        INDEX[Search Index]
        STORE[(Database)]
    end

    subgraph Outputs
        QA[Q&A Interface]
        SEARCH[Search Results]
        GRAPH[Knowledge Graph]
        CHR[CHR Reports]
    end

    PDF --> INGEST
    CSV --> INGEST
    API --> INGEST
    WEB --> INGEST
    IMG --> INGEST

    INGEST --> EXTRACT
    EXTRACT --> INDEX
    EXTRACT --> STORE
    STORE --> GRAPH

    INDEX --> QA
    INDEX --> SEARCH
    STORE --> QA
    STORE --> CHR
```

## Document Ingestion Flow

### End-to-End Document Processing

```mermaid
sequenceDiagram
    participant U as User/Browser
    participant F as Frontend
    participant B as Backend API
    participant P as Processor
    participant D as Database
    participant S as Search Index
    participant N as NATS

    U->>F: Upload file
    F->>B: POST /upload
    B->>B: Validate file
    B->>P: process_pdf/csv/xlsx
    P->>P: Extract content
    P->>P: Generate embeddings
    P->>D: Store artifacts
    P->>S: Index content
    B->>N: Publish ingest.> event
    B->>F: Return artifact ID
    F->>U: Show progress/results
```

### PDF Processing Pipeline

```mermaid
graph TD
    A[PDF Upload] --> B{Fast Mode?}
    B -->|Yes| C[Docling Basic]
    B -->|No| D[Docling Full + VLM]

    C --> E[Extract Text]
    D --> E
    D --> F[Analyze Images]
    D --> G[Detect Tables]

    E --> H{OCR Enabled?}
    H -->|Yes| I[Tesseract OCR]
    H -->|No| J[Text Only]
    I --> J

    F --> K[Image Descriptions]
    G --> L[Table Extraction]

    J --> M[Chunk Content]
    K --> M
    L --> M

    M --> N[Generate Embeddings]
    N --> O[Store in Database]
    N --> P[Add to Search Index]
    N --> Q[Extract to Neo4j]

    O --> R[Publish to NATS]
```

### Supported File Types

| File Type | Processor | Output Format |
|-----------|-----------|---------------|
| PDF | `pdf_processor.py` | Markdown + JSON metadata |
| CSV | `csv_processor.py` | Structured data + facts |
| XLSX/XLS | `xlsx_processor.py` | Structured data + facts |
| XML | `xml_ingestion.py` | Structured records |
| OpenAPI | `openapi_ingestion.py` | API catalog entries |
| Postman | `postman_ingestion.py` | API catalog entries |
| Web URL | `web_ingestion.py` | Markdown + assets |
| Images | `image_ocr.py` | Extracted text |
| Audio/Video | `media_transcriber.py` | Transcript + metadata |

## Search and Q&A Flow

### Semantic Search Flow

```mermaid
sequenceDiagram
    participant U as User
    participant F as Frontend
    participant B as Backend
    participant S as SearchIndex
    participant E as QAEngine
    participant D as Database

    U->>F: Enter search query
    F->>B: GET /search?q=query
    B->>S: generate_query_embedding()
    S->>S: FAISS search
    S->>B: Return ranked results
    B->>D: Fetch full evidence
    B->>F: Return search results
    F->>U: Display results
```

### Q&A with Citations

```mermaid
graph TD
    A[User Question] --> B[POST /ask]
    B --> C[Generate Query Embedding]
    C --> D[Search Index]
    D --> E[Retrieve Relevant Chunks]
    E --> F{Use HRM?}
    F -->|Yes| G[Halting Reasoning Module]
    F -->|No| H[Standard QA]
    G --> I[Iterative Refinement]
    H --> I
    I --> J[Generate Answer]
    J --> K[Add Citations]
    K --> L[Return Response]
```

### LLM Integration Flow

```mermaid
sequenceDiagram
    participant B as Backend
    participant TZ as TensorZero
    participant LLM as LLM Provider
    participant CH as ClickHouse

    B->>TZ: POST /v1/chat/completions
    TZ->>CH: Log request
    TZ->>LLM: Forward request
    LLM->>TZ: Return response
    TZ->>CH: Log response
    TZ->>B: Return response
    B->>B: Cache/response processing
```

## Agent Coordination Flow

### Agent Zero Task Execution

```mermaid
graph TD
    A[Task Request] --> B{Agent Mode?}
    B -->|Local| C[DoX Agent Zero]
    B -->|Remote| D[Parent Agent Zero]

    C --> E[Parse Task]
    E --> F{Requires Tool?}
    F -->|Cipher| G[Cipher Service]
    F -->|Search| H[Search API]
    F -->|Document| I[Document API]
    F -->|Geometry| J[Geometry Engine]

    G --> K[Execute Tool]
    H --> K
    I --> K
    J --> K

    K --> L[Publish to NATS]
    L --> M[Return Result]
```

### NATS Message Flow

```mermaid
graph LR
    subgraph Publishers
        BE[backend]
        AZ[agent-zero]
        CS[cipher-service]
    end

    subgraph NATS[nats:4222]
        S1[GEOMETRY Stream]
        S2[PMOVES Stream]
    end

    subgraph Subscribers
        FE[frontend WS]
        GE[geometry_engine]
        AC[agent_coordinator]
    end

    BE -->|tokenism.cgp.*| S1
    CS -->|geometry.*| S1
    AZ -->|pmoves.agent.*| S2
    BE -->|pmoves.ingest.*| S2

    S1 --> FE
    S1 --> GE
    S2 --> AC
```

### CHIT Geometry Packet Flow

```mermaid
sequenceDiagram
    participant BE as Backend
    participant GE as Geometry Engine
    participant CS as ChitService
    participant N as NATS
    participant FE as Frontend

    BE->>GE: Analyze embeddings
    GE->>GE: Detect curvature
    GE->>CS: Create CGP
    CS->>N: Publish tokenism.cgp.>
    N->>FE: WebSocket broadcast
    FE->>FE: Update visualizations
```

## Knowledge Graph Flow

### Neo4j Knowledge Extraction

```mermaid
graph TD
    A[Document Ingested] --> B[Entity Extraction]
    B --> C[Relationship Detection]
    C --> D{Dual Write?}
    D -->|Yes| E[Local Neo4j]
    D -->|Yes| F[Parent Neo4j]
    D -->|No| E

    E --> G[Query Local Graph]
    F --> H[Query Parent Graph]

    G --> I[Graph API Response]
    H --> I
```

### Graph Query Flow

```mermaid
sequenceDiagram
    participant U as User
    participant F as Frontend
    participant B as Backend
    participant N as Neo4j
    participant P as Parent Neo4j

    U->>F: Graph query request
    F->>B: GET /graph/query
    B->>B: Parse Cypher query
    B->>N: Execute local query
    alt Parent accessible
        B->>P: Execute parent query
        P->>B: Parent results
    end
    N->>B: Local results
    B->>B: Merge results
    B->>F: Return graph data
    F->>U: Display graph
```

## CHR Pipeline Flow

### Constellation Harvest Regularization

```mermaid
graph TD
    A[Artifact Ready] --> B[Trigger CHR]
    B --> C[Load Evidence]
    C --> D[Apply Regex Patterns]
    D --> E[Extract Metrics]
    E --> F[Apply Heuristics]
    F --> G[Generate CHR]
    G --> H[Write YAML]
    H --> I[Create Visualizations]
    I --> J[Publish to NATS]
```

### CHR Output Flow

```mermaid
sequenceDiagram
    participant API as API Client
    participant B as Backend
    participant C as CHR Pipeline
    participant D as Datavzrd

    API->>B: POST /chr/{artifact_id}
    B->>C: run_chr()
    C->>C: Extract facts
    C->>C: Generate CHR YAML
    C->>B: Return CHR path
    B->>D: Generate viz.yaml
    D->>B: Visualization ready
    B->>API: CHR complete
```

## Export Flows

### POML Export

```mermaid
graph TD
    A[Export Request] --> B[Select Artifacts]
    B --> C[Build POML Structure]
    C --> D[Add Documents]
    D --> E[Add CHR Data]
    E --> F[Add Graph Data]
    F --> G[Generate POML File]
    G --> H[Return Download]
```

### A2UI Protocol Flow

```mermaid
sequenceDiagram
    participant C as Client
    participant B as Backend
    participant A as A2UI Service

    C->>B: GET /.well-known/a2ui
    B->>A: Generate manifest
    A->>A: Build capability list
    A->>B: Return manifest
    B->>C: A2UI protocol response
```

## Real-time Update Flow

### WebSocket Updates

```mermaid
graph LR
    subgraph Backend
        EV[Event]
    end

    subgraph NATS
        MB[Message Bus]
    end

    subgraph Frontend
        WS[WebSocket]
        UI[UI Update]
    end

    EV -->|Publish| MB
    MB -->|Subscribe| WS
    WS -->|Dispatch| UI
```

### Watch Folder Processing

```mermaid
graph TD
    A[File Dropped] --> B[Detected by watchgod]
    B --> C[Debounce 1s]
    C --> D[File Stabilized?]
    D -->|No| A
    D -->|Yes| E[Trigger Ingestion]
    E --> F[Process File]
    F --> G[Store Artifact]
    G --> H[Publish Event]
```

## API Request Flow

### Authentication Flow

```mermaid
sequenceDiagram
    participant C as Client
    participant M as Security Middleware
    participant A as Auth Module
    participant H as Handler

    C->>M: Request with JWT
    M->>A: Validate token
    A->>A: Decode and verify
    A->>M: User context
    M->>H: Pass request with user
    H->>M: Response
    M->>C: Return response
```

### Rate Limiting Flow

```mermaid
graph TD
    A[Incoming Request] --> B[RateLimit Middleware]
    B --> C{Exempt Path?}
    C -->|Yes| D[Pass Through]
    C -->|No| E{Check Rate Limit}
    E -->|Under| D
    E -->|Exceeded| F[Return 429]
    D --> G[Next Handler]
```

## Data Storage Flow

### Database Write Path

```mermaid
graph TD
    A[Write Request] --> B{DB Backend?}
    B -->|SQLite| C[Write to SQLite]
    B -->|Supabase| D[Write to Supabase]
    B -->|Dual| E[Write to Both]
    C --> F[Confirm Write]
    D --> F
    E --> F
    F --> G[Publish Event]
```

### Search Index Updates

```mermaid
sequenceDiagram
    participant API as API Handler
    participant DB as Database
    participant SI as SearchIndex
    participant FAISS as FAISS/NumPy

    API->>DB: Create evidence
    DB->>API: Return evidence ID
    API->>SI: Add to index
    SI->>FAISS: Generate embedding
    FAISS->>FAISS: Add to index
    FAISS->>SI: Index updated
    SI->>API: Confirm
```

## Monitoring Flow

### Metrics Collection

```mermaid
graph LR
    subgraph Services
        S1[backend]
        S2[agent-zero]
        S3[cipher-service]
    end

    subgraph Metrics
        M1[/metrics endpoint]
    end

    subgraph Prometheus
        P[Scrape & Store]
    end

    subgraph Grafana
        G[Dashboards]
    end

    S1 --> M1
    S2 --> M1
    S3 --> M1
    M1 --> P
    P --> G
```

### Logging Flow

```mermaid
graph LR
    subgraph Services
        S[All Services]
    end

    subgraph Loki
        L[Log Aggregation]
    end

    subgraph Grafana
        G[Log Explorer]
    end

    S -->|stdout/stderr| L
    L --> G
```

## Error Handling Flow

### Retry Logic

```mermaid
graph TD
    A[Request Fails] --> B{Retryable?}
    B -->|No| C[Return Error]
    B -->|Yes| D{Retries < Max?}
    D -->|No| C
    D -->|Yes| E[Wait Backoff]
    E --> F[Retry Request]
    F --> G{Success?}
    G -->|Yes| H[Return Result]
    G -->|No| B
```

### Circuit Breaker Pattern

```mermaid
stateDiagram-v2
    [*] --> Closed
    Closed --> Open: Failure Threshold
    Open --> HalfOpen: Timeout
    HalfOpen --> Closed: Success
    HalfOpen --> Open: Failure
    Closed --> [*]: Normal
    Open --> [*]: Circuit Open
```
