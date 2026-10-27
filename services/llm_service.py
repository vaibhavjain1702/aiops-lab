"""
LLM Service — Model selection and generation through Ollama
Port: 8002
Endpoints: /generate, /health, /models
"""

import os
import time
import logging

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("llm_service")

app = FastAPI(title="AIOps LLM Service", version="1.0.0")

# --- Configuration ---
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://host.docker.internal:11434")
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "qwen2.5:3b")
NUM_CTX = int(os.getenv("NUM_CTX", "4096"))
NUM_PREDICT = int(os.getenv("NUM_PREDICT", "512"))
TEMPERATURE = float(os.getenv("TEMPERATURE", "0.1"))

# Embedding model should never appear as a generation option
EMBEDDING_MODELS = {"nomic-embed-text", "nomic-embed-text:latest"}

# Grounded prompt template for RAG-enabled generation
GROUNDED_PROMPT_TEMPLATE = """You are an AI DevOps Technical Support Assistant. Answer the question using ONLY the provided context. Follow these rules strictly:

1. Use the provided context as your primary evidence source.
2. Do NOT invent facts that are not supported by the context.
3. If the context does not contain enough information to answer the question, clearly state: "I don't have sufficient information in the available context to answer this question."
4. Answer the question directly and concisely.
5. When referencing information from the context, indicate the source.

CONTEXT:
{context}

QUESTION:
{question}

ANSWER:"""

# Direct prompt template for non-RAG generation
DIRECT_PROMPT_TEMPLATE = """You are an AI DevOps Technical Support Assistant. Answer the following question based on your training knowledge.

QUESTION:
{question}

ANSWER:"""


class GenerateRequest(BaseModel):
    question: str
    model: Optional[str] = None
    context: Optional[str] = None
    num_ctx: Optional[int] = None
    num_predict: Optional[int] = None
    temperature: Optional[float] = None


@app.get("/health")
def health():
    """Health check — verify Ollama connectivity."""
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(f"{OLLAMA_BASE_URL}/api/tags")
            response.raise_for_status()
            models = response.json().get("models", [])
            generation_models = [
                m["name"] for m in models
                if m["name"] not in EMBEDDING_MODELS
                and not any(m["name"].startswith(e) for e in EMBEDDING_MODELS)
            ]
            return {
                "status": "healthy",
                "service": "llm",
                "ollama_url": OLLAMA_BASE_URL,
                "default_model": DEFAULT_MODEL,
                "available_models": len(generation_models),
                "models": generation_models
            }
    except Exception as e:
        return {"status": "unhealthy", "service": "llm", "error": str(e)}


@app.get("/models")
def list_models():
    """List available generation models (filtering out embedding models)."""
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(f"{OLLAMA_BASE_URL}/api/tags")
            response.raise_for_status()
            models = response.json().get("models", [])
            
            generation_models = []
            for m in models:
                name = m["name"]
                # Filter out embedding models
                if name in EMBEDDING_MODELS or any(name.startswith(e.split(":")[0]) for e in EMBEDDING_MODELS if "embed" in e):
                    continue
                generation_models.append({
                    "name": name,
                    "size": m.get("size", 0),
                    "modified_at": m.get("modified_at", "")
                })
            
            return {
                "models": generation_models,
                "default": DEFAULT_MODEL,
                "count": len(generation_models)
            }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Cannot reach Ollama: {str(e)}")


@app.post("/generate")
def generate(request: GenerateRequest):
    """Generate a response using the specified model through Ollama."""
    model = request.model or DEFAULT_MODEL
    num_ctx = request.num_ctx or NUM_CTX
    num_predict = request.num_predict or NUM_PREDICT
    temperature = request.temperature or TEMPERATURE
    
    # Build prompt based on whether context is provided (RAG ON/OFF)
    if request.context and request.context.strip():
        prompt = GROUNDED_PROMPT_TEMPLATE.format(
            context=request.context,
            question=request.question
        )
        rag_mode = True
    else:
        prompt = DIRECT_PROMPT_TEMPLATE.format(
            question=request.question
        )
        rag_mode = False
    
    logger.info(f"Generating with model={model}, rag={rag_mode}, ctx_len={num_ctx}")
    
    try:
        start_time = time.time()
        
        with httpx.Client(timeout=120.0) as client:
            response = client.post(
                f"{OLLAMA_BASE_URL}/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "num_ctx": num_ctx,
                        "num_predict": num_predict,
                        "temperature": temperature
                    }
                }
            )
            response.raise_for_status()
        
        end_time = time.time()
        result = response.json()
        
        # Extract Ollama timing information
        answer = result.get("response", "").strip()
        total_duration = result.get("total_duration", 0)
        load_duration = result.get("load_duration", 0)
        prompt_eval_count = result.get("prompt_eval_count", 0)
        eval_count = result.get("eval_count", 0)
        eval_duration = result.get("eval_duration", 0)
        
        # Calculate tokens per second
        gen_tok_per_sec = 0.0
        if eval_duration > 0:
            gen_tok_per_sec = round(eval_count / (eval_duration / 1e9), 2)
        
        return {
            "answer": answer,
            "model": model,
            "rag_mode": rag_mode,
            "latency_seconds": round(end_time - start_time, 4),
            "prompt_tokens": prompt_eval_count,
            "response_tokens": eval_count,
            "total_tokens": prompt_eval_count + eval_count,
            "generation_tok_per_sec": gen_tok_per_sec,
            "ollama_total_duration": total_duration,
            "ollama_load_duration": load_duration,
            "ollama_eval_duration": eval_duration,
            "num_ctx": num_ctx,
            "num_predict": num_predict,
            "temperature": temperature
        }
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail=f"Generation timed out for model {model}")
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=502, detail=f"Ollama error: {e.response.text}")
    except Exception as e:
        logger.error(f"Generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
