"""
Models API Router

Provides endpoints for querying available models from:
- Ollama (local models)
- TensorZero (gateway models)
"""

import httpx
from fastapi import APIRouter, HTTPException
from typing import Dict, List, Any
from pydantic import BaseModel
import os

router = APIRouter()

# Model service URLs
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")
TENSORZERO_BASE_URL = os.getenv("TENSORZERO_BASE_URL", "http://tensorzero-gateway:3000")


class ModelInfo(BaseModel):
    """Basic model information"""
    name: str
    size: int | None = None
    digest: str | None = None
    details: Dict[str, Any] | None = None


class OllamaModelResponse(BaseModel):
    """Ollama models API response"""
    models: List[ModelInfo]


class TensorZeroModel(BaseModel):
    """TensorZero model info"""
    model_name: str
    provider: str | None = None
    type: str | None = None


@router.get("/", response_model=Dict[str, Any])
async def list_models() -> Dict[str, Any]:
    """
    Aggregate models from all available sources.

    Returns:
    {
        "ollama": [...],      # Models from Ollama
        "tensorzero": [...],  # Models configured in TensorZero
        "services": {         # Service availability status
            "ollama": "healthy" | "unavailable",
            "tensorzero": "healthy" | "unavailable"
        }
    }
    """
    result = {
        "ollama": [],
        "tensorzero": [],
        "services": {
            "ollama": "unknown",
            "tensorzero": "unknown"
        }
    }

    # Fetch Ollama models
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{OLLAMA_BASE_URL}/api/tags")
            if response.status_code == 200:
                data = response.json()
                result["ollama"] = data.get("models", [])
                result["services"]["ollama"] = "healthy"
            else:
                result["services"]["ollama"] = "unavailable"
    except Exception as e:
        result["services"]["ollama"] = f"error: {str(e)}"

    # Fetch TensorZero models
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            # TensorZero uses OpenAI-compatible /v1/models endpoint
            response = await client.get(
                f"{TENSORZERO_BASE_URL}/openai/v1/models",
                headers={"Authorization": "Bearer tensorzero"}
            )
            if response.status_code == 200:
                data = response.json()
                result["tensorzero"] = data.get("data", [])
                result["services"]["tensorzero"] = "healthy"
            else:
                result["services"]["tensorzero"] = "unavailable"
    except Exception as e:
        result["services"]["tensorzero"] = f"error: {str(e)}"

    return result


@router.post("/test/{model_name}", response_model=Dict[str, Any])
async def test_model(model_name: str, provider: str = "ollama", prompt: str = "Hello!") -> Dict[str, Any]:
    """
    Send a test inference request to a model.

    Args:
        model_name: Name of the model to test
        provider: "ollama" or "tensorzero"
        prompt: Test prompt to send

    Returns:
        Response from the model
    """
    if provider == "ollama":
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{OLLAMA_BASE_URL}/api/generate",
                    json={
                        "model": model_name,
                        "prompt": prompt,
                        "stream": False
                    }
                )
                if response.status_code == 200:
                    return response.json()
                else:
                    raise HTTPException(status_code=response.status_code, detail=response.text)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    elif provider == "tensorzero":
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{TENSORZERO_BASE_URL}/openai/v1/chat/completions",
                    headers={
                        "Authorization": "Bearer tensorzero",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": model_name,
                        "messages": [{"role": "user", "content": prompt}]
                    }
                )
                if response.status_code == 200:
                    return response.json()
                else:
                    raise HTTPException(status_code=response.status_code, detail=response.text)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    else:
        raise HTTPException(status_code=400, detail=f"Unknown provider: {provider}")


@router.get("/health", response_model=Dict[str, Any])
async def model_health() -> Dict[str, Any]:
    """
    Check health of all model services.
    """
    health_status = {
        "ollama": {"status": "unknown", "url": OLLAMA_BASE_URL},
        "tensorzero": {"status": "unknown", "url": TENSORZERO_BASE_URL}
    }

    # Check Ollama
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            response = await client.get(f"{OLLAMA_BASE_URL}/api/tags")
            health_status["ollama"]["status"] = "healthy" if response.status_code == 200 else "unhealthy"
    except Exception:
        health_status["ollama"]["status"] = "unreachable"

    # Check TensorZero
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            response = await client.get(f"{TENSORZERO_BASE_URL}/health")
            health_status["tensorzero"]["status"] = "healthy" if response.status_code == 200 else "unhealthy"
    except Exception:
        health_status["tensorzero"]["status"] = "unreachable"

    return health_status
