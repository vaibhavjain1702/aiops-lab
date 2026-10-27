"""
Ingestion Service — PDF/TXT/MD extraction, chunking, and indexing
Port: 8003
Endpoints: /ingest, /health
"""

import os
import io
import hashlib
import logging
import time
from typing import Optional

import httpx
from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ingestion_service")

app = FastAPI(title="AIOps Ingestion Service", version="1.0.0")

# --- Configuration ---
RETRIEVAL_URL = os.getenv("RETRIEVAL_URL", "http://retrieval:8001")
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "500"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "50"))


# --- Text Extraction ---
def extract_text_from_pdf(file_bytes: bytes) -> list[dict]:
    """Extract text from PDF, page by page."""
    try:
        from PyPDF2 import PdfReader
        reader = PdfReader(io.BytesIO(file_bytes))
        pages = []
        for i, page in enumerate(reader.pages):
            text = page.extract_text()
            if text and text.strip():
                pages.append({"text": text.strip(), "page": i + 1})
        return pages
    except Exception as e:
        logger.error(f"PDF extraction failed: {e}")
        raise HTTPException(status_code=400, detail=f"PDF extraction failed: {str(e)}")


def extract_text_from_txt(file_bytes: bytes) -> list[dict]:
    """Extract text from TXT file."""
    try:
        text = file_bytes.decode("utf-8", errors="ignore").strip()
        if not text:
            raise HTTPException(status_code=400, detail="TXT file is empty")
        return [{"text": text, "page": 1}]
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="Unable to decode TXT file")


def extract_text_from_md(file_bytes: bytes) -> list[dict]:
    """Extract text from Markdown file."""
    try:
        text = file_bytes.decode("utf-8", errors="ignore").strip()
        if not text:
            raise HTTPException(status_code=400, detail="Markdown file is empty")
        return [{"text": text, "page": 1}]
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="Unable to decode Markdown file")


# --- Text Processing ---
def normalize_text(text: str) -> str:
    """Normalize text: collapse whitespace, strip, etc."""
    import re
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()
    return text


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Split text into overlapping chunks."""
    text = normalize_text(text)
    if len(text) <= chunk_size:
        return [text]
    
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        
        # Try to break at sentence boundary
        if end < len(text):
            last_period = chunk.rfind('.')
            last_newline = chunk.rfind('\n')
            break_point = max(last_period, last_newline)
            if break_point > chunk_size * 0.5:
                chunk = text[start:start + break_point + 1]
                end = start + break_point + 1
        
        chunks.append(chunk.strip())
        start = end - overlap
    
    return [c for c in chunks if c]


# --- Indexing ---
def index_chunks(chunks: list[dict], source: str, document_id: str) -> dict:
    """Send chunks to retrieval service for indexing."""
    documents = []
    for chunk in chunks:
        doc = {
            "id": hashlib.md5(f"{document_id}_{chunk['chunk_index']}_{chunk['text'][:50]}".encode()).hexdigest(),
            "text": chunk["text"],
            "metadata": {
                "source": source,
                "page": chunk.get("page", 1),
                "chunk_index": chunk["chunk_index"],
                "document_id": document_id
            }
        }
        documents.append(doc)
    
    try:
        with httpx.Client(timeout=120.0) as client:
            response = client.post(
                f"{RETRIEVAL_URL}/upsert_batch",
                json={"documents": documents}
            )
            response.raise_for_status()
            return response.json()
    except Exception as e:
        logger.error(f"Indexing failed: {e}")
        raise HTTPException(status_code=502, detail=f"Retrieval service indexing failed: {str(e)}")


# --- Endpoints ---
@app.get("/health")
def health():
    """Health check for ingestion service."""
    # Check retrieval service connectivity
    retrieval_status = "unknown"
    try:
        with httpx.Client(timeout=5.0) as client:
            r = client.get(f"{RETRIEVAL_URL}/health")
            retrieval_status = "connected" if r.status_code == 200 else "error"
    except Exception:
        retrieval_status = "unreachable"
    
    return {
        "status": "healthy",
        "service": "ingestion",
        "retrieval_url": RETRIEVAL_URL,
        "retrieval_status": retrieval_status,
        "chunk_size": CHUNK_SIZE,
        "chunk_overlap": CHUNK_OVERLAP,
        "supported_formats": ["pdf", "txt", "md"]
    }


@app.post("/ingest")
async def ingest(
    file: UploadFile = File(...),
    source_name: Optional[str] = Form(None)
):
    """Ingest a document: extract, chunk, embed, and index."""
    filename = file.filename or "unknown"
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    source = source_name or filename
    
    if ext not in ("pdf", "txt", "md"):
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: .{ext}. Supported: .pdf, .txt, .md"
        )
    
    logger.info(f"Ingesting file: {filename} (type: {ext})")
    start_time = time.time()
    
    # Read file bytes
    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")
    
    # Extract text based on file type
    if ext == "pdf":
        pages = extract_text_from_pdf(file_bytes)
    elif ext == "txt":
        pages = extract_text_from_txt(file_bytes)
    elif ext == "md":
        pages = extract_text_from_md(file_bytes)
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported format: {ext}")
    
    if not pages:
        raise HTTPException(status_code=400, detail="No text could be extracted from the file")
    
    # Generate document ID
    document_id = hashlib.md5(f"{filename}_{time.time()}".encode()).hexdigest()[:12]
    
    # Chunk all pages
    all_chunks = []
    chunk_index = 0
    for page_data in pages:
        text_chunks = chunk_text(page_data["text"])
        for chunk_text_item in text_chunks:
            all_chunks.append({
                "text": chunk_text_item,
                "page": page_data.get("page", 1),
                "chunk_index": chunk_index
            })
            chunk_index += 1
    
    if not all_chunks:
        raise HTTPException(status_code=400, detail="No chunks could be created from the document")
    
    # Index chunks via retrieval service
    index_result = index_chunks(all_chunks, source, document_id)
    
    processing_time = time.time() - start_time
    
    return {
        "status": "success",
        "filename": filename,
        "source": source,
        "document_id": document_id,
        "file_type": ext,
        "pages_extracted": len(pages),
        "chunks_created": len(all_chunks),
        "chunks_indexed": index_result.get("upserted_count", len(all_chunks)),
        "total_collection_count": index_result.get("collection_count", 0),
        "processing_time_seconds": round(processing_time, 2),
        "chunk_size": CHUNK_SIZE,
        "chunk_overlap": CHUNK_OVERLAP
    }


@app.post("/ingest_text")
def ingest_text(
    text: str,
    source: str = "manual",
    document_id: Optional[str] = None
):
    """Ingest raw text directly (used for seeding knowledge base)."""
    if not text.strip():
        raise HTTPException(status_code=400, detail="Text is empty")
    
    doc_id = document_id or hashlib.md5(text[:100].encode()).hexdigest()[:12]
    
    chunks = chunk_text(text)
    all_chunks = []
    for i, chunk in enumerate(chunks):
        all_chunks.append({
            "text": chunk,
            "page": 1,
            "chunk_index": i
        })
    
    index_result = index_chunks(all_chunks, source, doc_id)
    
    return {
        "status": "success",
        "source": source,
        "document_id": doc_id,
        "chunks_created": len(all_chunks),
        "chunks_indexed": index_result.get("upserted_count", len(all_chunks)),
        "total_collection_count": index_result.get("collection_count", 0)
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)
