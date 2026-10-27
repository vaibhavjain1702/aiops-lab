# AI DevOps Technical Support Assistant

A **local, RAG-powered AI DevOps assistant** built with FastAPI, ChromaDB, Ollama, and Docker. Supports multi-model comparison, 7-category evaluation, guardrails, and isolated code execution.

## Architecture

```
Browser → FastAPI App :8000 → Retrieval :8001 → ChromaDB + Ollama (nomic-embed-text)
                             → LLM :8002      → Ollama (qwen2.5/starcoder2/codellama)
                             → Ingestion :8003 → Retrieval
                             → Code Runner :8004 (internal, isolated)
```

| Service | Port | Responsibility |
|---------|------|----------------|
| **app** | 8000 | UI, orchestration, ask/upload/seed/evaluation APIs, guardrails |
| **retrieval** | 8001 | Embeddings, ChromaDB, similarity search, document stats |
| **llm** | 8002 | Model selection, generation through Ollama |
| **ingestion** | 8003 | PDF/TXT/MD extraction, chunking, indexing |
| **code-runner** | 8004 | Execute generated code in isolated container |
| **Ollama** | 11434 | Local LLM and embedding runtime |

## Prerequisites

- Docker & Docker Compose
- Ollama installed and running
- ~8GB RAM recommended

## Ollama / Model Setup

```bash
# Install Ollama (if not already)
curl -fsSL https://ollama.com/install.sh | sh

# Pull required models
ollama pull qwen2.5:3b
ollama pull starcoder2:3b
ollama pull codellama
ollama pull nomic-embed-text

# Verify
ollama list
```

### Recommended Ollama settings:
```bash
# /etc/systemd/system/ollama.service.d/override.conf
Environment="OLLAMA_HOST=0.0.0.0:11434"
Environment="OLLAMA_MAX_LOADED_MODELS=1"
Environment="OLLAMA_KEEP_ALIVE=0"
Environment="OLLAMA_NUM_PARALLEL=1"
```

## Docker Setup

```bash
# Copy and configure environment
cp .env.example .env
# Edit .env if needed (e.g., OLLAMA_BASE_URL for your setup)

# Validate compose file
docker compose -f docker-compose.yml config -q

# Build and start base services
docker compose -f docker-compose.yml up -d --build

# Or full stack with code runner:
docker compose -f docker-compose.yml -f docker-compose.live.yml up -d --build
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_BASE_URL` | `http://host.docker.internal:11434` | Ollama API URL |
| `DEFAULT_MODEL` | `qwen2.5:3b` | Default generation model |
| `EMBEDDING_MODEL` | `nomic-embed-text:latest` | Embedding model |
| `RELEVANCE_THRESHOLD` | `0.25` | Minimum similarity for retrieval |
| `DEFAULT_TOP_K` | `5` | Default number of retrieved chunks |
| `CHUNK_SIZE` | `500` | Characters per chunk |
| `CHUNK_OVERLAP` | `50` | Overlap between chunks |
| `MAX_INPUT_LENGTH` | `2000` | Maximum question length |

## Startup & Verification

```bash
# Start
docker compose -f docker-compose.yml -f docker-compose.live.yml up -d --build

# Check services
docker compose ps

# Health check
curl -s http://localhost:8000/health | python3 -m json.tool

# View logs
docker compose logs --tail=100
```

## Seeding the Knowledge Base

```bash
# Via API
curl -X POST http://localhost:8000/seed

# Or via the dashboard: Knowledge Base → Seed Built-in Knowledge
```

The built-in knowledge covers 20+ DevOps topics including Docker, Kubernetes, Prometheus, Grafana, RAG, FastAPI, ChromaDB, and more.

## Uploading Documents

Supported formats: **PDF, TXT, MD**

- **Dashboard**: Drag & drop or click the upload area
- **API**: `curl -X POST -F "file=@document.pdf" http://localhost:8000/upload`

**Important**: Uploading documents indexes them for retrieval. It does **NOT** train or fine-tune the LLM.

## RAG Explanation

**RAG (Retrieval-Augmented Generation)** workflow:
1. Question → embedding via nomic-embed-text
2. Embedding → cosine similarity search in ChromaDB
3. Top-K relevant chunks retrieved (filtered by threshold)
4. Chunks assembled as context for the LLM
5. Grounded prompt instructs LLM to use context as evidence
6. Answer returned with sources, similarity scores, and telemetry

**RAG ON**: Grounded answers with source attribution
**RAG OFF**: Direct model answers from training knowledge

## Evaluation Methodology

### Seven Categories
| Category | Tests |
|----------|-------|
| Explanation | Technical concept explanation |
| Code Retrieval | Locate relevant code/context |
| Dependency Understanding | Service/component relationships |
| Bug Analysis | Diagnose errors, explain fixes |
| Code Generation | Generate usable code |
| Refactoring | Improve code preserving behavior |
| RAG based Question | Answer using retrieved knowledge |

### Metrics
| Metric | Method | Limitation |
|--------|--------|------------|
| Correctness | Token F1 (reference match) | Automated proxy, not semantic truth |
| Relevance | Keyword overlap | Can miss nuance |
| Hallucination Rate | Unsupported claim heuristic | Must be labeled heuristic |
| Retrieval Quality | Avg/top cosine similarity | Not proof of correctness |
| Code Test Pass Rate | Passed/total tests | Depends on test quality |
| Latency | End-to-end duration | Hardware dependent |
| P95 Latency | 95th percentile | Needs multiple runs |
| Token Usage | Prompt + response tokens | Model specific |

### Running the Benchmark
```bash
# Run full 105-evaluation benchmark (35 questions × 3 models)
python evaluation/evaluate_models.py

# Generate graphs
python evaluation/create_source_graph.py
```

**⚠️ Only run after the application is stable. Do NOT rerun for cosmetic changes.**

## Guardrails

### Input Guardrails
- Empty question rejection
- Length limit (>2000 chars)
- Prompt injection detection (15+ patterns)
- Out-of-scope detection

### Output Guardrails
- Empty output rejection
- Internal error string detection
- Groundedness check (heuristic, when RAG active)

### Demo
```bash
# Run guardrail demo
curl -X POST http://localhost:8000/guardrails/demo | python3 -m json.tool
```

## Code Runner

The isolated code runner executes generated code in a separate container with:
- Read-only filesystem
- 256MB memory limit
- 0.5 CPU limit
- 64 PID limit
- AST validation (rejects dangerous imports/builtins)
- 10-second execution timeout

**⚠️ This is a classroom/local evaluation runner, NOT a production security boundary.**

## Result Locations

| File | Contents |
|------|----------|
| `evaluation/category_evaluation_results.json` | All 105 evaluation results |
| `evaluation/category_summary.json` | Category × model summary |
| `evaluation/category_summary.csv` | CSV export |
| `evaluation/evaluation_results_rag.json` | RAG-enabled results |
| `evaluation/evaluation_results_no_rag.json` | No-RAG results |
| `evaluation/codebase_qa_results.json` | Codebase QA results |
| `evaluation/output_test_results.json` | AI output test results |
| `evaluation/live_runs.jsonl` | Live evaluation log |
| `docs/evaluation_graphs/` | Generated PNG charts |

## Project Specification

The full project requirements and design (Weeks 1 to 5) are in
[`docs/AI_DevOps_Assistant_Master_Project_Specification_Weeks_1_to_5.docx`](docs/AI_DevOps_Assistant_Master_Project_Specification_Weeks_1_to_5.docx).
UI feature notes are in [`docs/ui_features.md`](docs/ui_features.md).

## Stop / Reset

```bash
# Stop services (preserves data)
docker compose -f docker-compose.yml -f docker-compose.live.yml down

# ⚠️ DANGER: Reset everything including ChromaDB data
docker compose -f docker-compose.yml -f docker-compose.live.yml down -v
```

## Troubleshooting

| Symptom | First Check | Likely Area |
|---------|-------------|-------------|
| App won't start | `docker compose logs app` | Python import/syntax/deps |
| Generation fails | LLM health + Ollama status | Ollama networking/model |
| No retrieval | `/health` + `/stats` | Knowledge base not seeded |
| Upload not retrieved | Upload response + similarity | Extraction/chunking |
| No models in UI | `/models` endpoint | Ollama discovery |
| Slow generation | Latency + load duration | RAM/model load |
| Guardrail not blocking | Test with known injection | Enforcement path |

## Known Limitations

- All automated metrics are proxy measures — human review needed for truth
- Code runner is classroom-grade, not production security
- Source frequency graph is RAG retrieval frequency, NOT code dependency
- Performance depends on local hardware (CPU/RAM)
- One generation model loaded at a time for memory management
- Local laptop/VM performance ≠ cloud-scale performance
