from fastapi import FastAPI
from .models import IngestRequest, AskRequest, ChatRequest, ChatResponse
from .tools import rag
from .agent import Agent

app = FastAPI(title="Copilot Agent (Starter)")
agent = Agent()

@app.post("/ingest")
def ingest(req: IngestRequest):
    n = rag.ingest_path(req.path)
    return {"status": "ok", "chunks_indexed": n}

@app.post("/ask")
def ask(req: AskRequest):
    return rag.ask(req.query)

@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    messages = [{"role": m.role, "content": m.content} for m in req.messages]
    res = agent.chat(messages)
    return ChatResponse(answer=res["answer"], steps=res.get("steps", []))
