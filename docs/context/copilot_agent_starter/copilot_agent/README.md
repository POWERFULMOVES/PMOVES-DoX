# Copilot Agent (Starter)

A minimal **Copilot-style agent** with:
- **FastAPI** service (`/chat`, `/ingest`, `/ask`) 
- **ReAct-style planner** that selects tools
- **RAG** over local documents (FAISS + Sentence-Transformers)
- **Report generator** tool (turns tabular data into clean summaries)
- **Model adapter**: works with OpenAI if `OPENAI_API_KEY` is set; otherwise uses a deterministic mock

> Designed for **MVPs**, internal sandboxes, and team demos. Drop it into your org, point at a docs folder, and go.

## Quickstart

```bash
# using uv (recommended)
uv venv
uv pip install -e .[openai]   # or: uv pip install -e .
cp .env.example .env          # add keys if using OpenAI

# run
uvicorn app.main:app --reload --port 8080
```

## Endpoints

- `POST /ingest` — index a folder of documents (txt, md, csv, xlsx, pdf->txt pre-parsed)
- `POST /ask` — semantic search over indexed docs (RAG without LLM)
- `POST /chat` — agentic chat with tools (planner may call: `rag.search`, `reports.summarize_table`)

### Example
```bash
curl -X POST localhost:8080/ingest -H "content-type: application/json"   -d '{"path": "sample_data"}'

curl -X POST localhost:8080/ask -H "content-type: application/json"   -d '{"query": "What is ROAS?"}'
```

## Notes
- PDF parsing is **not** included; provide pre-extracted text (e.g., via Docling) or add a parser.
- The planner is intentionally simple and transparent. Extend with function-calling as needed.
