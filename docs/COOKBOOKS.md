# PMOVES-DoX Cookbooks

Practical recipes and step-by-step tutorials for common use cases.

## Table of Contents

1. [Cookbook 1: Financial Statement Analysis Pipeline](#cookbook-1-financial-statement-analysis-pipeline)
2. [Cookbook 2: Log Analysis and Error Tracking](#cookbook-2-log-analysis-and-error-tracking)
3. [Cookbook 3: API Documentation from OpenAPI](#cookbook-3-api-documentation-from-openapi)
4. [Cookbook 4: Research Paper Clustering](#cookbook-4-research-paper-clustering)
5. [Cookbook 5: LMS Tag Extraction for Training Materials](#cookbook-5-lms-tag-extraction-for-training-materials)
6. [Cookbook 6: Multi-Source Intelligence Gathering](#cookbook-6-multi-source-intelligence-gathering)
7. [Cookbook 7: Contract Analysis and Q&A](#cookbook-7-contract-analysis-and-qa)
8. [Cookbook 8: Marketing Performance Dashboard](#cookbook-8-marketing-performance-dashboard)

---

## Cookbook 1: Financial Statement Analysis Pipeline (🚧 Planned / Coming Soon)

**Scenario:** You have quarterly financial reports in PDF format and need to extract tables, detect financial statements, and create a searchable knowledge base.

### Prerequisites
- Docker installed
- Sample financial PDFs (or use samples/financials/)

### Step 1: Environment Setup

```bash
# Clone and start
git clone https://github.com/POWERFULMOVES/PMOVES-DoX.git
cd PMOVES-DoX

# Create environment file
cat > backend/.env <<EOF
PORT=8484
FRONTEND_ORIGIN=http://localhost:3737
PDF_FINANCIAL_ANALYSIS=true
DOCLING_VLM_REPO=ibm-granite/granite-docling-258M
HUGGINGFACE_HUB_TOKEN=your_token_here
EOF

# Start services
docker compose up -d
```

### Step 2: Upload Financial Reports

```bash
# Upload Q1-Q4 reports
for quarter in Q1 Q2 Q3 Q4; do
  curl -X POST http://localhost:8484/upload \
    -F "files=@financials/2024_${quarter}_report.pdf" \
    -F "report_week=2024-W$((quarter * 13))"
done
```

**What's happening:**
- Each PDF is processed by Docling
- Tables are extracted and merged across pages
- Financial statements are detected
- VLM generates captions for charts

### Step 3: Verify Financial Detection

```bash
# Check detected statements
curl http://localhost:8484/analysis/financials | jq

# Sample output:
{
  "statements": [
    {
      "artifact_id": "uuid-q1",
      "type": "income_statement",
      "page": 5,
      "confidence": 0.94,
      "metrics": {
        "revenue": "$1.2M",
        "net_income": "$340K"
      }
    },
    {
      "artifact_id": "uuid-q1",
      "type": "balance_sheet",
      "page": 7,
      "confidence": 0.89
    }
  ]
}
```

### Step 4: Query Specific Metrics

```bash
# Q&A interface
curl -X POST "http://localhost:8484/ask" \
  --data-urlencode "question=What was total revenue across all quarters?" \
  | jq

# Response with citations
{
  "answer": "Total revenue was $5.8M ($1.2M Q1 + $1.5M Q2 + $1.6M Q3 + $1.5M Q4)",
  "citations": [
    {
      "artifact_id": "uuid-q1",
      "page": 5,
      "content": "Q1 Revenue: $1.2M"
    },
    // ... more citations
  ],
  "confidence": 0.92
}
```

### Step 5: Semantic Search

```bash
# Search for profit margins
curl -X POST http://localhost:8484/search \
  -H "Content-Type: application/json" \
  -d '{
    "q": "profit margin percentage",
    "types": ["pdf"],
    "k": 10
  }' | jq

# Filter by quarter
curl -X POST http://localhost:8484/search \
  -d '{"q":"Q2 expenses breakdown","k":5}' | jq
```

### Step 6: Export for Microsoft Copilot

```bash
# Get document IDs
DOCS=$(curl -s http://localhost:8484/documents | jq -r '.documents[].id')

# Export each as POML
for doc_id in $DOCS; do
  curl -X POST http://localhost:8484/export/poml \
    -H "Content-Type: application/json" \
    -d "{\"document_id\":\"$doc_id\",\"variant\":\"catalog\"}" \
    | jq -r '.rel' \
    | xargs -I {} curl -s "http://localhost:8484/download?rel={}" \
    > "copilot_${doc_id}.poml"
done
```

### Step 7: Generate Dashboard

```bash
# Combine all financial data
curl -X POST http://localhost:8484/structure/chr \
  -d '{
    "artifact_id": "uuid-q1",
    "K": 4,
    "units_mode": "sentences"
  }' | jq

# Start datavzrd
docker compose --profile tools up -d datavzrd

# Open http://localhost:5173
```

### Expected Results

✅ **Extracted:**
- Income statements from all quarters
- Balance sheets with assets/liabilities
- Cash flow statements
- YoY comparison tables

✅ **Queryable:**
- "What was operating expense in Q3?"
- "How did net income change from Q2 to Q3?"
- "Which quarter had highest revenue?"

✅ **Exportable:**
- POML files for Copilot integration
- CSV exports of tables
- Interactive datavzrd dashboards

---

## Cookbook 2: Log Analysis and Error Tracking

**Scenario:** You have XML application logs from multiple services and need to track errors, identify patterns, and export reports.

### Step 1: Prepare XPath Mapping

Create a mapping file for your log format:

```yaml
# config/xpath_map.yaml
entry: "//logEntry | //event"
fields:
  ts: "./timestamp | ./@time"
  level: "./severity | ./level"
  code: "./errorCode | ./eventId"
  component: "./service | ./component | ./source"
  message: "./message | ./description"
```

### Step 2: Configure Backend

```bash
# Set environment
cat > backend/.env <<EOF
PORT=8484
XML_XPATH_MAP_FILE=/app/config/xpath_map.yaml
EOF

# Mount config in docker-compose.yml
# Add to backend volumes:
#   - ./config:/app/config
```

### Step 3: Ingest Logs

```bash
# Upload log files
curl -X POST http://localhost:8484/upload \
  -F "files=@logs/payment-service-2024-01.xml" \
  -F "report_week=2024-W04"

# Or direct ingestion
curl -X POST http://localhost:8484/ingest/xml \
  -H "Content-Type: application/json" \
  -d '{"filepath":"logs/auth-service-2024-01.xml"}'
```

### Step 4: Filter and Analyze

```bash
# Get all errors
curl "http://localhost:8484/logs?level=ERROR" | jq

# Filter by time range
curl "http://localhost:8484/logs?level=ERROR&from=2024-01-15T00:00:00Z&to=2024-01-20T23:59:59Z" | jq

# Filter by component
curl "http://localhost:8484/logs?component=payment-service&level=ERROR" | jq

# Search error codes
curl "http://localhost:8484/logs?code=E1001" | jq
```

### Step 5: Export Reports

```bash
# Export all errors to CSV
curl "http://localhost:8484/logs/export?level=ERROR" > errors.csv

# Import to Excel or analyze with pandas
python3 <<EOF
import pandas as pd
df = pd.read_csv('errors.csv')
print(df.groupby('code').size().sort_values(ascending=False))
print(df.groupby('component')['code'].count())
EOF
```

### Step 6: Create Dashboard

```bash
# Generate datavzrd for logs
curl -X POST http://localhost:8484/viz/datavzrd/logs \
  -H "Content-Type: application/json" \
  -d '{
    "level": "ERROR",
    "from": "2024-01-01T00:00:00Z",
    "to": "2024-01-31T23:59:59Z"
  }' | jq

# Start visualization
docker compose --profile tools up -d datavzrd
```

### Step 7: Set Up Alerts (Custom Script)

```python
#!/usr/bin/env python3
# scripts/log_monitor.py
import requests
import time
from datetime import datetime, timedelta

API_BASE = "http://localhost:8484"
ALERT_THRESHOLD = 10  # errors per minute

def check_errors():
    now = datetime.utcnow()
    one_min_ago = now - timedelta(minutes=1)

    params = {
        "level": "ERROR",
        "from": one_min_ago.isoformat() + "Z",
        "to": now.isoformat() + "Z"
    }

    resp = requests.get(f"{API_BASE}/logs", params=params)
    logs = resp.json().get("logs", [])

    if len(logs) >= ALERT_THRESHOLD:
        print(f"⚠️  ALERT: {len(logs)} errors in last minute!")
        # Send to Slack/email/PagerDuty

    return len(logs)

# Run every minute
while True:
    count = check_errors()
    print(f"{datetime.now()}: {count} errors")
    time.sleep(60)
```

### Expected Results

✅ **Visibility:**
- Real-time error tracking
- Component-level breakdown
- Time-series analysis

✅ **Insights:**
- Top error codes
- Service dependencies
- Peak error times

✅ **Automation:**
- Automated alerting
- CSV exports for reporting
- Dashboard for stakeholders

---

## Cookbook 3: API Documentation from OpenAPI

**Scenario:** Convert OpenAPI/Swagger specifications into searchable documentation with POML export.

### Step 1: Collect OpenAPI Specs

```bash
# Organize specs
mkdir -p specs/{v1,v2,v3}

# Download from services
curl https://api.example.com/openapi.json > specs/v3/main-api.json
curl https://payments.example.com/swagger.yaml > specs/v3/payments.yaml
```

### Step 2: Ingest All Specs

```bash
# Batch ingestion
for spec in specs/v3/*.json specs/v3/*.yaml; do
  curl -X POST http://localhost:8484/ingest/openapi \
    -H "Content-Type: application/json" \
    -d "{\"filepath\":\"$spec\"}"
done

# Or via upload
curl -X POST http://localhost:8484/upload \
  -F "files=@specs/v3/main-api.json" \
  -F "files=@specs/v3/payments.yaml"
```

### Step 3: Browse API Catalog

```bash
# List all APIs
curl http://localhost:8484/apis | jq

# Sample output:
{
  "apis": [
    {
      "id": "uuid1",
      "artifact_id": "uuid-spec1",
      "path": "/users",
      "method": "POST",
      "operation_id": "createUser",
      "summary": "Create a new user",
      "tags": ["users"]
    },
    // ... more endpoints
  ]
}

# Get specific endpoint
curl http://localhost:8484/apis/uuid1 | jq

# Detailed view:
{
  "path": "/users",
  "method": "POST",
  "operation_id": "createUser",
  "summary": "Create a new user",
  "parameters": [
    {
      "name": "body",
      "in": "body",
      "required": true,
      "schema": {
        "type": "object",
        "properties": {
          "username": {"type": "string"},
          "email": {"type": "string"}
        }
      }
    }
  ],
  "responses": {
    "201": {
      "description": "User created",
      "schema": {"$ref": "#/definitions/User"}
    }
  }
}
```

### Step 4: Search APIs

```bash
# Search by functionality
curl -X POST http://localhost:8484/search \
  -d '{"q":"create user","types":["api"],"k":5}' | jq

# Find authentication endpoints
curl -X POST http://localhost:8484/search \
  -d '{"q":"authentication oauth token","types":["api"]}' | jq

# Find all payment methods
curl -X POST http://localhost:8484/search \
  -d '{"q":"payment methods","types":["api"]}' | jq
```

### Step 5: Generate Documentation

```bash
# Export to POML for each spec
curl -s http://localhost:8484/documents | jq -r '.documents[] | select(.filetype==".json") | .id' | while read doc_id; do
  curl -X POST http://localhost:8484/export/poml \
    -d "{\"document_id\":\"$doc_id\",\"variant\":\"catalog\",\"title\":\"API Reference\"}" \
    | jq -r '.rel' \
    | xargs -I {} curl -s "http://localhost:8484/download?rel={}" \
    > "docs/api_${doc_id}.poml"
done

# Convert to markdown (custom script)
python3 <<EOF
import json
import requests

resp = requests.get("http://localhost:8484/apis")
apis = resp.json()["apis"]

with open("API_REFERENCE.md", "w") as f:
    f.write("# API Reference\n\n")

    for api in apis:
        f.write(f"## {api['method']} {api['path']}\n\n")
        f.write(f"{api.get('summary', 'No description')}\n\n")
        f.write(f"**Operation ID:** {api.get('operation_id', 'N/A')}\n\n")
        f.write(f"**Tags:** {', '.join(api.get('tags', []))}\n\n")
        f.write("---\n\n")

print("✅ Generated API_REFERENCE.md")
EOF
```

### Step 6: Create Interactive Search UI

```html
<!-- docs/api-search.html -->
<!DOCTYPE html>
<html>
<head>
  <title>API Search</title>
  <style>
    body { font-family: sans-serif; max-width: 800px; margin: 50px auto; }
    #search { width: 100%; padding: 10px; font-size: 16px; }
    .result { border: 1px solid #ddd; margin: 10px 0; padding: 15px; }
    .method { font-weight: bold; color: #2196F3; }
  </style>
</head>
<body>
  <h1>API Search</h1>
  <input type="text" id="search" placeholder="Search APIs...">
  <div id="results"></div>

  <script>
    const searchInput = document.getElementById('search');
    const resultsDiv = document.getElementById('results');

    searchInput.addEventListener('input', async (e) => {
      const query = e.target.value;
      if (!query) {
        resultsDiv.innerHTML = '';
        return;
      }

      const resp = await fetch('http://localhost:8484/search', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({q: query, types: ['api'], k: 10})
      });

      const data = await resp.json();
      resultsDiv.innerHTML = data.results.map(r => `
        <div class="result">
          <span class="method">${r.method || 'GET'}</span> ${r.content}
        </div>
      `).join('');
    });
  </script>
</body>
</html>
```

### Expected Results

✅ **Centralized API Catalog:**
- All endpoints in one place
- Searchable by path, method, description
- Organized by service/spec

✅ **Developer Portal:**
- Interactive search
- POML exports for Copilot
- Markdown documentation

✅ **Integration:**
- Import to Postman
- Link to code generation tools
- CI/CD validation

---

## Cookbook 4: Research Paper Clustering

**Scenario:** You have hundreds of research papers (PDFs) and want to organize them into thematic clusters.

### Step 1: Bulk Upload

```bash
# Upload all papers
find papers/ -name "*.pdf" -type f | while read pdf; do
  curl -X POST http://localhost:8484/upload \
    -F "files=@$pdf" \
    -F "report_week=2024-W20"
done

# Or parallel upload
find papers/ -name "*.pdf" | xargs -P 4 -I {} \
  curl -s -X POST http://localhost:8484/upload -F "files=@{}"
```

### Step 2: Rebuild Search Index

```bash
# After bulk upload
curl -X POST http://localhost:8484/search/rebuild
```

### Step 3: Extract Entities

```bash
# Get named entities from all papers
curl "http://localhost:8484/analysis/entities" | jq

# Sample output:
{
  "entities": [
    {"text": "BERT", "label": "TECHNOLOGY", "count": 45},
    {"text": "Stanford University", "label": "ORG", "count": 23},
    {"text": "neural networks", "label": "CONCEPT", "count": 67}
  ]
}
```

### Step 4: Run CHR Clustering

```bash
# Get first artifact ID
ARTIFACT_ID=$(curl -s http://localhost:8484/artifacts | jq -r '.artifacts[0].id')

# Run CHR with 8 clusters
curl -X POST http://localhost:8484/structure/chr \
  -H "Content-Type: application/json" \
  -d "{
    \"artifact_id\": \"$ARTIFACT_ID\",
    \"K\": 8,
    \"units_mode\": \"paragraphs\",
    \"cluster_params\": {
      \"min_samples\": 3,
      \"min_cluster_size\": 5
    }
  }" | jq

# Output includes:
# - chr_clusters.csv (paragraphs with cluster IDs)
# - chr_pca.png (visualization)
# - chr_relation_strength.csv (similarity matrix)
```

### Step 5: Analyze Clusters

```python
#!/usr/bin/env python3
# scripts/analyze_clusters.py
import pandas as pd
import matplotlib.pyplot as plt

# Load clusters
df = pd.read_csv('backend/artifacts/chr_clusters.csv')

# Cluster sizes
cluster_sizes = df.groupby('cluster_id').size()
print("Cluster Sizes:")
print(cluster_sizes)

# Top terms per cluster
for cluster_id in df['cluster_id'].unique():
    cluster_docs = df[df['cluster_id'] == cluster_id]
    print(f"\n=== Cluster {cluster_id} ===")
    print(f"Size: {len(cluster_docs)}")
    print(f"Sample texts:")
    for text in cluster_docs['text'].head(3):
        print(f"  - {text[:100]}...")

# Visualize
plt.figure(figsize=(10, 6))
cluster_sizes.plot(kind='bar')
plt.title('Papers per Cluster')
plt.xlabel('Cluster ID')
plt.ylabel('Count')
plt.savefig('cluster_distribution.png')
print("\n✅ Saved cluster_distribution.png")
```

### Step 6: Label Clusters (Manual)

```bash
# Review clusters and assign labels
cat > cluster_labels.json <<EOF
{
  "0": "Deep Learning",
  "1": "Natural Language Processing",
  "2": "Computer Vision",
  "3": "Reinforcement Learning",
  "4": "Graph Neural Networks",
  "5": "Transfer Learning",
  "6": "Federated Learning",
  "7": "Explainable AI"
}
EOF
```

### Step 7: Generate Dashboard

```bash
# Create datavzrd config
cat > backend/artifacts/datavzrd.yaml <<EOF
name: Research Paper Clusters
datasets:
  papers:
    path: chr_clusters.csv
    separator: ","
views:
  cluster_view:
    dataset: papers
    desc: Papers organized by theme
    page-size: 50
    columns:
      cluster_id:
        plot:
          heatmap:
            scale: linear
      text:
        display-mode: normal
EOF

# Start datavzrd
docker compose --profile tools up -d datavzrd
# Open http://localhost:5173
```

### Expected Results

✅ **Organization:**
- 8 thematic clusters
- Similar papers grouped together
- Outliers identified

✅ **Insights:**
- Research trends
- Topic distribution
- Citation networks

✅ **Deliverables:**
- Cluster visualization
- Labeled categories
- Interactive dashboard

---

## Cookbook 5: LMS Tag Extraction for Training Materials

**Scenario:** Extract Learning Management System (LMS) tags from training documents for course cataloging.

### Step 1: Configure LangExtract

```bash
# Use Google Gemini
export LANGEXTRACT_API_KEY=your-gemini-api-key
export LANGEXTRACT_MODEL=gemini-2.5-flash

# Or use local Ollama
docker run -d -v ollama:/root/.ollama -p 11434:11434 ollama/ollama
docker exec -it ollama_container ollama pull gemma3

export LANGEXTRACT_PROVIDER=ollama
export LANGEXTRACT_MODEL=ollama:gemma3
export OLLAMA_BASE_URL=http://localhost:11434
```

### Step 2: Upload Training Materials

```bash
# Upload course PDFs
curl -X POST http://localhost:8484/upload \
  -F "files=@courses/python_basics.pdf" \
  -F "files=@courses/advanced_sql.pdf" \
  -F "files=@courses/leadership_101.pdf"
```

### Step 3: Extract Tags (Dry Run)

```bash
# Get document ID
DOC_ID=$(curl -s http://localhost:8484/documents | jq -r '.documents[0].id')

# Preview tags
curl -X POST http://localhost:8484/extract/tags \
  -H "Content-Type: application/json" \
  -d "{
    \"document_id\": \"$DOC_ID\",
    \"preset\": \"lms_comprehensive\",
    \"dry_run\": true
  }" | jq

# Sample output:
{
  "tags": [
    {
      "name": "Python",
      "category": "Programming Languages",
      "confidence": 0.95
    },
    {
      "name": "Beginner",
      "category": "Difficulty Level",
      "confidence": 0.88
    },
    {
      "name": "Data Structures",
      "category": "Skills",
      "confidence": 0.91
    }
  ]
}
```

### Step 4: Persist Tags

```bash
# Extract and save
curl -X POST http://localhost:8484/extract/tags \
  -d "{
    \"document_id\": \"$DOC_ID\",
    \"preset\": \"lms_comprehensive\",
    \"dry_run\": false,
    \"use_hrm\": true
  }" | jq
```

### Step 5: Query Tags

```bash
# Get all tags
curl "http://localhost:8484/tags" | jq

# Filter by document
curl "http://localhost:8484/tags?document_id=$DOC_ID" | jq

# Search tags
curl -X POST http://localhost:8484/search \
  -d '{"q":"python programming","types":["tag"]}' | jq
```

### Step 6: Batch Extraction

```bash
# Extract tags from all documents
curl -s http://localhost:8484/documents | jq -r '.documents[].id' | while read doc_id; do
  echo "Processing $doc_id..."
  curl -s -X POST http://localhost:8484/extract/tags \
    -d "{\"document_id\":\"$doc_id\",\"preset\":\"lms_skills\"}" \
    > /dev/null
done
```

### Step 7: Export Tag Catalog

```python
#!/usr/bin/env python3
# scripts/export_tags.py
import requests
import pandas as pd

resp = requests.get("http://localhost:8484/tags")
tags = resp.json()["tags"]

df = pd.DataFrame(tags)

# Group by category
for category, group in df.groupby('category'):
    print(f"\n=== {category} ===")
    for tag in group['name'].unique():
        count = len(group[group['name'] == tag])
        print(f"  {tag} ({count} courses)")

# Export to Excel
df.to_excel("lms_tag_catalog.xlsx", index=False)
print("\n✅ Exported to lms_tag_catalog.xlsx")
```

### Expected Results

✅ **Tag Taxonomy:**
- Skills (Python, SQL, Leadership)
- Difficulty (Beginner, Intermediate, Advanced)
- Duration (1-hour, half-day, full-day)
- Competencies (Technical, Soft Skills)

✅ **Applications:**
- Course recommendations
- Learning path generation
- Skill gap analysis

---

## Cookbook 6: Multi-Source Intelligence Gathering

**Scenario:** Combine PDFs, web pages, APIs, and logs to create a comprehensive intelligence database.

### Step 1: Web Scraping

```bash
# Ingest competitor websites
curl -X POST http://localhost:8484/upload \
  -F "urls=https://competitor1.com/products" \
  -F "urls=https://competitor2.com/pricing" \
  -F "urls=https://competitor3.com/features"
```

### Step 2: API Monitoring

```bash
# Ingest OpenAPI specs
curl -X POST http://localhost:8484/ingest/openapi \
  -d '{"filepath":"specs/competitor-api-v2.json"}'
```

### Step 3: Document Analysis

```bash
# Upload market research PDFs
curl -X POST http://localhost:8484/upload \
  -F "files=@research/market_analysis_2024.pdf" \
  -F "files=@research/competitor_landscape.pdf"
```

### Step 4: Log Correlation

```bash
# Ingest usage logs
curl -X POST http://localhost:8484/ingest/xml \
  -d '{"filepath":"logs/user_activity.xml"}'
```

### Step 5: Cross-Source Search

```bash
# Search across all sources
curl -X POST http://localhost:8484/search \
  -d '{"q":"pricing strategy","k":20}' | jq

# Results from PDFs, APIs, web pages
```

### Step 6: Q&A Intelligence

```bash
# Ask strategic questions
curl -X POST "http://localhost:8484/ask" \
  --data-urlencode "question=What pricing models do competitors use?" \
  | jq

curl -X POST "http://localhost:8484/ask" \
  --data-urlencode "question=What API features are most common?" \
  | jq
```

### Expected Results

✅ **360° View:**
- Competitor analysis
- Market trends
- API capabilities
- User behavior

✅ **Intelligence Reports:**
- Automated summaries
- Cross-source insights
- Trend detection

---

## Cookbook 7: Contract Analysis and Q&A

**Scenario:** Analyze legal contracts, extract key terms, and enable Q&A.

### Step 1: Upload Contracts

```bash
# Upload multiple contracts
curl -X POST http://localhost:8484/upload \
  -F "files=@contracts/vendor_agreement_2024.pdf" \
  -F "files=@contracts/nda_template.pdf" \
  -F "files=@contracts/sla_document.pdf"
```

### Step 2: Extract Key Terms

```bash
# Search for specific clauses
curl -X POST http://localhost:8484/search \
  -d '{"q":"termination clause","types":["pdf"]}' | jq

curl -X POST http://localhost:8484/search \
  -d '{"q":"liability limitations","types":["pdf"]}' | jq

curl -X POST http://localhost:8484/search \
  -d '{"q":"payment terms net 30","types":["pdf"]}' | jq
```

### Step 3: Q&A on Contracts

```bash
# Ask questions
curl -X POST "http://localhost:8484/ask" \
  --data-urlencode "question=What is the notice period for termination?" | jq

curl -X POST "http://localhost:8484/ask" \
  --data-urlencode "question=What are the payment terms?" | jq

curl -X POST "http://localhost:8484/ask" \
  --data-urlencode "question=What is the liability cap?" | jq
```

### Step 4: Generate Comparison

```python
import requests
import pandas as pd

questions = [
    "What is the termination notice period?",
    "What are the payment terms?",
    "What is the liability cap?",
    "What is the renewal clause?"
]

docs = requests.get("http://localhost:8484/documents").json()["documents"]

comparison = []
for doc in docs:
    row = {"Contract": doc["filename"]}
    for q in questions:
        resp = requests.post(
            "http://localhost:8484/ask",
            params={"question": q}
        )
        row[q] = resp.json().get("answer", "N/A")
    comparison.append(row)

df = pd.DataFrame(comparison)
df.to_excel("contract_comparison.xlsx")
```

---

## Cookbook 8: Marketing Performance Dashboard

**Scenario:** Analyze marketing campaign data from CSV files and create interactive dashboards.

### Step 1: Upload Campaign Data

```bash
# Upload performance CSVs
curl -X POST http://localhost:8484/upload \
  -F "files=@marketing/q1_campaigns.csv" \
  -F "files=@marketing/q2_campaigns.csv" \
  -F "report_week=2024-W26"
```

### Step 2: Run CHR Analysis

```bash
ARTIFACT_ID=$(curl -s http://localhost:8484/artifacts | jq -r '.artifacts[0].id')

curl -X POST http://localhost:8484/structure/chr \
  -d "{\"artifact_id\":\"$ARTIFACT_ID\",\"K\":5}" | jq
```

### Step 3: Generate Dashboard

```bash
docker compose --profile tools up -d datavzrd
# Open http://localhost:5173
```

### Step 4: Export Summary

```bash
curl -X POST http://localhost:8484/summaries/generate \
  -d '{"style":"executive","scope":"workspace"}' | jq
```

---

## Next Steps

- 📖 See [USER_GUIDE.md](./USER_GUIDE.md) for feature reference
- 🎨 Check [DEMOS.md](./DEMOS.md) for video walkthroughs
- 🔧 Read [API_REFERENCE.md](./API_REFERENCE.md) for API details

**Need help?** Open an issue on GitHub!
