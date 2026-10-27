"""
Retrieval Service — ChromaDB + Embeddings via Ollama (nomic-embed-text)
Port: 8001
Endpoints: /health, /stats, /documents, /retrieve, /upsert, /clear
"""

import os
import time
import hashlib
import logging
from typing import Optional

import httpx
import chromadb
from fastapi import FastAPI, Query, HTTPException
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("retrieval_service")

app = FastAPI(title="AIOps Retrieval Service", version="1.0.0")

# --- Configuration ---
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://host.docker.internal:11434")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "nomic-embed-text:latest")
CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", "./data/chroma")
COLLECTION_NAME = "devops_knowledge"

# --- ChromaDB Client ---
chroma_client = None
collection = None


def get_collection():
    """Lazy-initialize ChromaDB client and collection."""
    global chroma_client, collection
    if collection is None:
        chroma_client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
        collection = chroma_client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"}
        )
        logger.info(f"ChromaDB collection '{COLLECTION_NAME}' initialized with {collection.count()} documents")
    return collection


def generate_embedding(text: str) -> list:
    """Generate embedding using Ollama nomic-embed-text."""
    try:
        with httpx.Client(timeout=60.0) as client:
            response = client.post(
                f"{OLLAMA_BASE_URL}/api/embeddings",
                json={"model": EMBEDDING_MODEL, "prompt": text}
            )
            response.raise_for_status()
            return response.json()["embedding"]
    except Exception as e:
        logger.error(f"Embedding generation failed: {e}")
        raise HTTPException(status_code=503, detail=f"Embedding service unavailable: {str(e)}")


# --- Pydantic Models ---
class UpsertRequest(BaseModel):
    id: Optional[str] = None
    text: str
    metadata: Optional[dict] = None


class UpsertBatchRequest(BaseModel):
    documents: list[dict]


# --- Endpoints ---
@app.get("/health")
def health():
    """Health check for retrieval service."""
    try:
        col = get_collection()
        count = col.count()
        return {
            "status": "healthy",
            "service": "retrieval",
            "collection": COLLECTION_NAME,
            "document_count": count,
            "embedding_model": EMBEDDING_MODEL,
            "chroma_persist_dir": CHROMA_PERSIST_DIR
        }
    except Exception as e:
        return {"status": "unhealthy", "service": "retrieval", "error": str(e)}


@app.get("/stats")
def stats():
    """Return statistics about the knowledge base."""
    try:
        col = get_collection()
        count = col.count()
        
        # Get unique sources
        all_data = col.get(include=["metadatas"])
        sources = set()
        documents_set = set()
        for meta in all_data.get("metadatas", []):
            if meta:
                sources.add(meta.get("source", "unknown"))
                documents_set.add(meta.get("document_id", "unknown"))
        
        return {
            "total_chunks": count,
            "total_documents": len(documents_set),
            "unique_sources": list(sources),
            "source_count": len(sources),
            "collection": COLLECTION_NAME,
            "embedding_model": EMBEDDING_MODEL
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/documents")
def list_documents():
    """List all documents and their chunks."""
    try:
        col = get_collection()
        all_data = col.get(include=["metadatas", "documents"])
        
        documents = {}
        for i, meta in enumerate(all_data.get("metadatas", [])):
            if meta:
                doc_id = meta.get("document_id", "unknown")
                if doc_id not in documents:
                    documents[doc_id] = {
                        "document_id": doc_id,
                        "source": meta.get("source", "unknown"),
                        "chunk_count": 0,
                        "chunks": []
                    }
                documents[doc_id]["chunk_count"] += 1
                documents[doc_id]["chunks"].append({
                    "chunk_index": meta.get("chunk_index", i),
                    "text_preview": all_data["documents"][i][:100] + "..." if all_data["documents"][i] else "",
                    "page": meta.get("page", None)
                })
        
        return {
            "total_documents": len(documents),
            "total_chunks": col.count(),
            "documents": list(documents.values())
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/retrieve")
def retrieve(
    query: str = Query(..., description="Search query"),
    top_k: int = Query(5, ge=1, le=20, description="Number of results")
):
    """Retrieve top-k similar chunks from ChromaDB."""
    try:
        col = get_collection()
        
        if col.count() == 0:
            return {
                "query": query,
                "results": [],
                "total_results": 0,
                "message": "Knowledge base is empty. Please seed or upload documents first."
            }
        
        # Generate query embedding
        query_embedding = generate_embedding(query)
        
        # Query ChromaDB
        start_time = time.time()
        results = col.query(
            query_embeddings=[query_embedding],
            n_results=min(top_k, col.count()),
            include=["documents", "metadatas", "distances"]
        )
        retrieval_time = time.time() - start_time
        
        # Format results with similarity scoring
        formatted_results = []
        for i in range(len(results["ids"][0])):
            distance = results["distances"][0][i]
            similarity = 1.0 - distance  # Convert cosine distance to similarity
            
            meta = results["metadatas"][0][i] if results["metadatas"][0] else {}
            formatted_results.append({
                "id": results["ids"][0][i],
                "text": results["documents"][0][i],
                "distance": round(distance, 4),
                "similarity": round(similarity, 4),
                "source": meta.get("source", "unknown"),
                "page": meta.get("page", None),
                "chunk_index": meta.get("chunk_index", None),
                "document_id": meta.get("document_id", "unknown")
            })
        
        return {
            "query": query,
            "results": formatted_results,
            "total_results": len(formatted_results),
            "retrieval_time_seconds": round(retrieval_time, 4),
            "embedding_model": EMBEDDING_MODEL
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/upsert")
def upsert(request: UpsertRequest):
    """Upsert a single document chunk into ChromaDB."""
    try:
        col = get_collection()
        
        # Generate ID if not provided
        doc_id = request.id or hashlib.md5(request.text.encode()).hexdigest()
        
        # Generate embedding
        embedding = generate_embedding(request.text)
        
        # Prepare metadata
        metadata = request.metadata or {}
        metadata["indexed_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        
        # Upsert into ChromaDB
        col.upsert(
            ids=[doc_id],
            documents=[request.text],
            embeddings=[embedding],
            metadatas=[metadata]
        )
        
        return {
            "status": "success",
            "id": doc_id,
            "collection_count": col.count()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upsert failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/upsert_batch")
def upsert_batch(request: UpsertBatchRequest):
    """Batch upsert multiple document chunks."""
    try:
        col = get_collection()
        
        ids = []
        documents = []
        embeddings = []
        metadatas = []
        
        for doc in request.documents:
            text = doc.get("text", "")
            doc_id = doc.get("id", hashlib.md5(text.encode()).hexdigest())
            meta = doc.get("metadata", {})
            meta["indexed_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
            
            embedding = generate_embedding(text)
            
            ids.append(doc_id)
            documents.append(text)
            embeddings.append(embedding)
            metadatas.append(meta)
        
        col.upsert(
            ids=ids,
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas
        )
        
        return {
            "status": "success",
            "upserted_count": len(ids),
            "collection_count": col.count()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Batch upsert failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/clear")
def clear():
    """Clear all documents from the collection."""
    global collection
    try:
        col = get_collection()
        # Delete and recreate collection
        chroma_client.delete_collection(COLLECTION_NAME)
        collection = chroma_client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"}
        )
        return {"status": "cleared", "collection": COLLECTION_NAME, "count": 0}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
