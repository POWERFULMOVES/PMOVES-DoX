from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class IngestRequest(BaseModel):
    path: str = Field(..., description="Folder path to ingest documents from")

class AskRequest(BaseModel):
    query: str

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    context: Optional[Dict[str, Any]] = None

class ChatResponse(BaseModel):
    answer: str
    steps: List[Dict[str, Any]] = []
