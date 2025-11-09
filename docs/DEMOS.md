# PMOVES-DoX Demos & Example Scenarios

Interactive demonstrations and example workflows with sample data.

## Table of Contents

1. [Demo 1: 5-Minute Quick Start](#demo-1-5-minute-quick-start)
2. [Demo 2: Financial Report Analysis](#demo-2-financial-report-analysis)
3. [Demo 3: API Documentation Generator](#demo-3-api-documentation-generator)
4. [Demo 4: Log Analytics Dashboard](#demo-4-log-analytics-dashboard)
5. [Demo 5: Research Paper Organizer](#demo-5-research-paper-organizer)
6. [Sample Data Repository](#sample-data-repository)
7. [Video Walkthroughs](#video-walkthroughs)

---

## Demo 1: 5-Minute Quick Start

**Goal:** Get PMOVES-DoX running and process your first document in 5 minutes.

### Prerequisites
- Docker Desktop installed
- 5 minutes of your time

### Step 1: Clone and Start (1 minute)

```bash
# Clone repository
git clone https://github.com/POWERFULMOVES/PMOVES-DoX.git
cd PMOVES-DoX

# Start with Docker Compose
docker compose -f docker-compose.cpu.yml up -d

# Wait for services to be ready (~30 seconds)
docker compose logs -f backend | grep "Application startup complete"
```

### Step 2: Open UI (30 seconds)

```bash
# Open in browser
open http://localhost:3737

# Or manually visit:
# Frontend: http://localhost:3737
# Backend API: http://localhost:8484
```

### Step 3: Upload Sample (1 minute)

```bash
# Via UI: Click "Choose Files" → Select samples/sample.csv

# Or via CLI:
curl -X POST http://localhost:8484/upload \
  -F "files=@samples/sample.csv" \
  -F "report_week=2024-W20"
```

**What happens:**
- CSV is processed
- Facts are extracted from each row
- Metrics calculated (CTR, conversions)
- Data indexed for search

### Step 4: Explore Facts (1 minute)

1. Click **Facts** tab
2. See extracted facts from CSV rows
3. Click page number to see evidence
4. Use search to filter: "revenue"

### Step 5: Ask a Question (1 minute)

1. Click **Q&A** tab
2. Type: "What is the total revenue?"
3. Get answer with citations
4. Click citation to see source

### Step 6: Semantic Search (1 minute)

1. Use global search bar (top right)
2. Search: "highest performing campaign"
3. Get results across all artifacts
4. Filter by type if needed

### ✅ Done!

You've successfully:
- Started PMOVES-DoX
- Uploaded a document
- Extracted facts
- Ran Q&A
- Performed semantic search

**Next:** Try uploading your own PDFs or CSVs!

---

## Demo 2: Financial Report Analysis

**Goal:** Extract and analyze financial statements from annual reports.

### Sample Data

Download sample financial PDFs:
```bash
# Create samples directory
mkdir -p samples/financials

# Download sample reports (or use your own)
# For demo purposes, we'll create a simple financial PDF
```

### Demo Script

```bash
#!/bin/bash
# demos/financial_analysis_demo.sh

set -e

echo "🏦 PMOVES-DoX Financial Analysis Demo"
echo "======================================"

# 1. Check services
echo "✓ Checking services..."
curl -s http://localhost:8484/health > /dev/null && echo "  Backend: UP" || exit 1

# 2. Upload financial report
echo "✓ Uploading financial report..."
UPLOAD_RESP=$(curl -s -X POST http://localhost:8484/upload \
  -F "files=@samples/financials/financial_statements.pdf" \
  -F "report_week=2024-W01")

echo "$UPLOAD_RESP" | jq -r '.results[] | "  Processed: \(.filename) - \(.facts_count) facts"'

# 3. Wait for processing
sleep 2

# 4. Check financial detection
echo "✓ Detecting financial statements..."
FINANCIAL=$(curl -s http://localhost:8484/analysis/financials)
echo "$FINANCIAL" | jq -r '.statements[] | "  Found: \(.type) on page \(.page) (confidence: \(.confidence))"'

# 5. Extract tables
echo "✓ Extracting tables..."
ARTIFACT_ID=$(echo "$UPLOAD_RESP" | jq -r '.results[0].artifact_id')
ARTIFACT=$(curl -s "http://localhost:8484/artifacts/$ARTIFACT_ID")
echo "$ARTIFACT" | jq -r '"  Tables: \(.table_evidence)"'

# 6. Ask questions
echo "✓ Running Q&A..."
QUESTIONS=(
  "What is the total revenue?"
  "What is the net income?"
  "What are the total assets?"
)

for q in "${QUESTIONS[@]}"; do
  ANSWER=$(curl -s -X POST "http://localhost:8484/ask" --data-urlencode "question=$q")
  echo "  Q: $q"
  echo "  A: $(echo "$ANSWER" | jq -r '.answer')"
  echo ""
done

# 7. Export POML
echo "✓ Exporting to POML..."
DOC_ID=$(curl -s http://localhost:8484/documents | jq -r '.documents[0].id')
POML=$(curl -s -X POST http://localhost:8484/export/poml \
  -H "Content-Type: application/json" \
  -d "{\"document_id\":\"$DOC_ID\",\"variant\":\"catalog\",\"title\":\"Financial Analysis\"}")

POML_FILE=$(echo "$POML" | jq -r '.rel')
echo "  POML saved: $POML_FILE"

echo ""
echo "✅ Demo complete!"
echo "   - Financial statements detected"
echo "   - Tables extracted"
echo "   - Q&A enabled"
echo "   - POML exported for Copilot"
```

### Run Demo

```bash
chmod +x demos/financial_analysis_demo.sh
./demos/financial_analysis_demo.sh
```

### Expected Output

```
🏦 PMOVES-DoX Financial Analysis Demo
======================================
✓ Checking services...
  Backend: UP
✓ Uploading financial report...
  Processed: financial_statements.pdf - 24 facts
✓ Detecting financial statements...
  Found: income_statement on page 5 (confidence: 0.94)
  Found: balance_sheet on page 7 (confidence: 0.89)
  Found: cash_flow_statement on page 9 (confidence: 0.87)
✓ Extracting tables...
  Tables: 8
✓ Running Q&A...
  Q: What is the total revenue?
  A: Total revenue for 2024 was $5.8 million.

  Q: What is the net income?
  A: Net income was $1.2 million.

  Q: What are the total assets?
  A: Total assets were $12.4 million.

✓ Exporting to POML...
  POML saved: artifacts/poml_uuid.poml

✅ Demo complete!
   - Financial statements detected
   - Tables extracted
   - Q&A enabled
   - POML exported for Copilot
```

---

## Demo 3: API Documentation Generator

**Goal:** Convert OpenAPI specs to searchable documentation.

### Sample Data

```bash
# Download sample OpenAPI specs
curl https://petstore3.swagger.io/api/v3/openapi.json > samples/sample_openapi.json
```

### Demo Script

```python
#!/usr/bin/env python3
# demos/api_documentation_demo.py

import requests
import json
import time
from pathlib import Path

API_BASE = "http://localhost:8484"

def demo():
    print("🔌 PMOVES-DoX API Documentation Generator")
    print("==========================================\n")

    # 1. Upload OpenAPI spec
    print("✓ Uploading OpenAPI specification...")
    files = {"files": open("samples/sample_openapi.json", "rb")}
    resp = requests.post(f"{API_BASE}/upload", files=files)
    result = resp.json()["results"][0]
    print(f"  Processed: {result['filename']}")
    print(f"  Evidence: {result['evidence_count']} items\n")

    time.sleep(1)

    # 2. List all APIs
    print("✓ Listing API endpoints...")
    apis = requests.get(f"{API_BASE}/apis").json()["apis"]
    print(f"  Total endpoints: {len(apis)}")

    # Group by method
    by_method = {}
    for api in apis:
        method = api.get("method", "GET")
        by_method.setdefault(method, 0)
        by_method[method] += 1

    for method, count in sorted(by_method.items()):
        print(f"    {method}: {count}")
    print()

    # 3. Search APIs
    print("✓ Searching APIs...")
    queries = ["create pet", "user authentication", "store inventory"]

    for q in queries:
        search_resp = requests.post(
            f"{API_BASE}/search",
            json={"q": q, "types": ["api"], "k": 3}
        )
        results = search_resp.json()["results"]
        print(f"  Query: '{q}'")
        for r in results[:2]:
            print(f"    - {r['content'][:60]}...")
        print()

    # 4. Get endpoint details
    print("✓ Endpoint details...")
    if apis:
        api_id = apis[0]["id"]
        detail = requests.get(f"{API_BASE}/apis/{api_id}").json()
        print(f"  {detail['method']} {detail['path']}")
        print(f"  Summary: {detail.get('summary', 'N/A')}")
        print(f"  Parameters: {len(detail.get('parameters', []))}")
        print()

    # 5. Export to POML
    print("✓ Exporting to POML...")
    docs = requests.get(f"{API_BASE}/documents").json()["documents"]
    if docs:
        doc_id = docs[0]["id"]
        poml_resp = requests.post(
            f"{API_BASE}/export/poml",
            json={"document_id": doc_id, "variant": "catalog", "title": "API Reference"}
        )
        poml_file = poml_resp.json()["rel"]
        print(f"  POML generated: {poml_file}")

    print("\n✅ Demo complete!")
    print("   - OpenAPI spec ingested")
    print("   - Endpoints cataloged")
    print("   - Searchable documentation created")
    print("   - POML exported for Copilot")

if __name__ == "__main__":
    demo()
```

### Run Demo

```bash
chmod +x demos/api_documentation_demo.py
python3 demos/api_documentation_demo.py
```

---

## Demo 4: Log Analytics Dashboard

**Goal:** Analyze XML logs and create interactive dashboard.

### Sample Data

```xml
<!-- samples/sample.xml -->
<logs>
  <log>
    <timestamp>2024-01-15T10:30:00Z</timestamp>
    <level>ERROR</level>
    <code>E1001</code>
    <component>payment-service</component>
    <message>Payment gateway timeout</message>
  </log>
  <log>
    <timestamp>2024-01-15T10:31:00Z</timestamp>
    <level>ERROR</level>
    <code>E1001</code>
    <component>payment-service</component>
    <message>Retry failed</message>
  </log>
  <log>
    <timestamp>2024-01-15T10:32:00Z</timestamp>
    <level>INFO</level>
    <code>I2001</code>
    <component>user-service</component>
    <message>User logged in successfully</message>
  </log>
</logs>
```

### Demo Script

```bash
#!/bin/bash
# demos/log_analytics_demo.sh

set -e

echo "📊 PMOVES-DoX Log Analytics Demo"
echo "================================="

# 1. Configure XPath mapping
export XML_XPATH_MAP='{"entry":"//log","fields":{"ts":"./timestamp","level":"./level","code":"./code","component":"./component","message":"./message"}}'

# 2. Ingest logs
echo "✓ Ingesting logs..."
curl -s -X POST http://localhost:8484/upload \
  -F "files=@samples/sample.xml" > /dev/null
echo "  Logs uploaded"

sleep 1

# 3. Query errors
echo "✓ Querying errors..."
ERRORS=$(curl -s "http://localhost:8484/logs?level=ERROR")
ERROR_COUNT=$(echo "$ERRORS" | jq '.logs | length')
echo "  Total errors: $ERROR_COUNT"

# 4. Group by component
echo "✓ Errors by component:"
echo "$ERRORS" | jq -r '.logs | group_by(.component) | .[] | "  \(.[0].component): \(length)"'

# 5. Export CSV
echo "✓ Exporting to CSV..."
curl -s "http://localhost:8484/logs/export?level=ERROR" > errors.csv
echo "  Saved: errors.csv ($(wc -l < errors.csv) lines)"

# 6. Generate dashboard
echo "✓ Generating dashboard..."
curl -s -X POST http://localhost:8484/viz/datavzrd/logs \
  -H "Content-Type: application/json" \
  -d '{"level":"ERROR"}' | jq -r '.viz_file'

echo ""
echo "✅ Demo complete!"
echo "   Start datavzrd: docker compose --profile tools up datavzrd"
echo "   Open: http://localhost:5173"
```

---

## Demo 5: Research Paper Organizer

**Goal:** Upload PDFs and organize into thematic clusters.

### Demo Script

```python
#!/usr/bin/env python3
# demos/research_organizer_demo.py

import requests
import time
from pathlib import Path

API_BASE = "http://localhost:8484"

def demo():
    print("📚 PMOVES-DoX Research Paper Organizer")
    print("======================================\n")

    # Simulate having research papers
    papers = [
        "Deep Learning for NLP.pdf",
        "BERT Architecture.pdf",
        "Transfer Learning Methods.pdf",
        "Computer Vision Survey.pdf",
        "ResNet Implementation.pdf"
    ]

    print(f"✓ Simulating upload of {len(papers)} papers...")
    print("  (In real scenario, upload actual PDFs)\n")

    # In real scenario:
    # for paper in papers:
    #     files = {"files": open(f"papers/{paper}", "rb")}
    #     requests.post(f"{API_BASE}/upload", files=files)

    # 2. Rebuild index
    print("✓ Rebuilding search index...")
    requests.post(f"{API_BASE}/search/rebuild")
    time.sleep(1)

    # 3. Extract entities
    print("✓ Extracting named entities...")
    entities = requests.get(f"{API_BASE}/analysis/entities").json()
    print(f"  Found {len(entities.get('entities', []))} unique entities")

    # 4. Get structure
    print("✓ Analyzing document structure...")
    structure = requests.get(f"{API_BASE}/analysis/structure").json()
    print(f"  Detected {len(structure.get('headings', []))} heading levels")

    # 5. Run CHR
    print("✓ Running CHR clustering...")
    artifacts = requests.get(f"{API_BASE}/artifacts").json()["artifacts"]
    if artifacts:
        chr_resp = requests.post(
            f"{API_BASE}/structure/chr",
            json={
                "artifact_id": artifacts[0]["id"],
                "K": 5,
                "units_mode": "paragraphs"
            }
        )
        result = chr_resp.json()
        print(f"  Created {result.get('K', 5)} clusters")
        print(f"  PCA visualization: {result.get('artifacts', {}).get('pca_plot', 'N/A')}")

    print("\n✅ Demo complete!")
    print("   - Papers analyzed")
    print("   - Entities extracted")
    print("   - Clusters created")
    print("   - Visualization ready")

if __name__ == "__main__":
    demo()
```

---

## Sample Data Repository

### Included Samples

The repository includes sample files for testing:

```
samples/
├── sample.csv              # Marketing campaign data
├── sample.xml              # Application logs
├── sample_openapi.json     # OpenAPI specification
├── sample_postman.json     # Postman collection
├── sample_audio.txt        # Audio transcript
├── sample_image.txt        # Image OCR
├── sample_video.txt        # Video transcript
└── financials/
    └── financial_statements.pdf  # Sample financial report
```

### Usage

```bash
# Load all samples
curl -X POST http://localhost:8484/load_samples

# Or individual samples
curl -X POST http://localhost:8484/upload -F "files=@samples/sample.csv"
curl -X POST http://localhost:8484/upload -F "files=@samples/sample.xml"
```

### Creating Your Own Samples

**CSV Format:**
```csv
date,campaign,impressions,clicks,revenue
2024-01-01,Summer Sale,12000,245,1500
2024-01-02,Winter Promo,14500,298,1820
```

**XML Log Format:**
```xml
<logs>
  <log>
    <timestamp>2024-01-01T10:00:00Z</timestamp>
    <level>ERROR</level>
    <code>E500</code>
    <component>api-server</component>
    <message>Internal server error</message>
  </log>
</logs>
```

---

## Video Walkthroughs

### Available Demos

1. **Quick Start Tutorial** (5 min)
   - Installation
   - First upload
   - Basic navigation

2. **Financial Analysis** (10 min)
   - PDF upload
   - Table extraction
   - Q&A demo

3. **API Documentation** (8 min)
   - OpenAPI ingestion
   - Search features
   - POML export

4. **Log Analytics** (12 min)
   - XML configuration
   - Filtering & search
   - Dashboard creation

5. **Advanced Features** (15 min)
   - CHR clustering
   - Tag extraction
   - Multi-source search

### Recording Your Own Demo

```bash
# Use asciinema for terminal recording
asciinema rec demo.cast

# Run your demo commands
./demos/financial_analysis_demo.sh

# Stop recording (Ctrl+D)

# Play back
asciinema play demo.cast

# Upload to asciinema.org
asciinema upload demo.cast
```

---

## Interactive Playground

### Jupyter Notebook Demo

```python
# demos/playground.ipynb

import requests
import pandas as pd
import matplotlib.pyplot as plt

API_BASE = "http://localhost:8484"

# 1. Upload data
with open("samples/sample.csv", "rb") as f:
    resp = requests.post(f"{API_BASE}/upload", files={"files": f})
print(resp.json())

# 2. Get facts
facts = requests.get(f"{API_BASE}/facts").json()["facts"]
df = pd.DataFrame(facts)
df.head()

# 3. Search
search_resp = requests.post(
    f"{API_BASE}/search",
    json={"q": "revenue", "k": 10}
)
results = pd.DataFrame(search_resp.json()["results"])
results[["content", "score"]].head()

# 4. Visualize
plt.figure(figsize=(10, 6))
plt.bar(results["content"], results["score"])
plt.xticks(rotation=45, ha="right")
plt.title("Search Results")
plt.tight_layout()
plt.show()
```

---

## Automated Testing

### Smoke Test Demo

```bash
# Run full smoke test suite
cd smoke
python smoke_backend.py

# Run security tests
python smoke_security.py

# Expected: All tests pass
[ OK ] /health
[ OK ] /upload
[ OK ] /facts
[ OK ] /search
...
```

---

## Next Steps

- 📖 Read [USER_GUIDE.md](./USER_GUIDE.md) for detailed features
- 🍳 Follow [COOKBOOKS.md](./COOKBOOKS.md) for recipes
- 🔧 Check [API_REFERENCE.md](./API_REFERENCE.md) for API docs

**Questions?** Open an issue on GitHub!
