# DevOps Knowledge Base

## Prometheus

Prometheus is an open-source systems monitoring and alerting toolkit originally built at SoundCloud. It is now a standalone open-source project and is maintained independently of any company. Prometheus collects and stores its metrics as time series data. Metrics information is stored with the timestamp at which it was recorded, alongside optional key-value pairs called labels.

### Key Features of Prometheus
- A multi-dimensional data model with time series data identified by metric name and key/value pairs
- PromQL, a flexible query language to leverage this dimensionality
- No reliance on distributed storage; single server nodes are autonomous
- Time series collection happens via a pull model over HTTP
- Pushing time series is supported via an intermediary gateway
- Targets are discovered via service discovery or static configuration
- Multiple modes of graphing and dashboarding support

### Prometheus Architecture
Prometheus scrapes metrics from instrumented jobs, either directly or via an intermediary push gateway for short-lived jobs. It stores all scraped samples locally and runs rules over this data to either aggregate and record new time series from existing data or generate alerts. Grafana or other API consumers can be used to visualize the collected data.

### Common Prometheus Metrics
- Counter: A cumulative metric that represents a single monotonically increasing counter
- Gauge: A metric that represents a single numerical value that can arbitrarily go up and down
- Histogram: Samples observations and counts them in configurable buckets
- Summary: Similar to a histogram but also provides total count and sum of observations

## Grafana

Grafana is an open-source platform for monitoring and observability. It allows you to query, visualize, alert on and understand your metrics no matter where they are stored. Grafana provides tools to create dashboards with panels, each representing specific metrics over a set time period.

### Grafana Dashboard Features
- Rich visualization options including graphs, tables, heatmaps, and gauges
- Support for multiple data sources including Prometheus, Elasticsearch, InfluxDB
- Template variables for creating dynamic and reusable dashboards
- Alerting rules that can be configured per panel
- Annotations for marking events on graphs
- Dashboard sharing and export capabilities

### Grafana with Prometheus Integration
Grafana integrates seamlessly with Prometheus. You add Prometheus as a data source in Grafana, and then use PromQL queries to create visualizations. Common dashboards include system metrics (CPU, memory, disk), application metrics (request rate, error rate, latency), and infrastructure metrics (container health, network traffic).

## Docker

Docker is a platform for developing, shipping, and running applications in containers. Containers are lightweight, standalone, executable packages that include everything needed to run a piece of software: code, runtime, system tools, libraries, and settings.

### Docker Architecture
Docker uses a client-server architecture. The Docker client talks to the Docker daemon, which does the heavy lifting of building, running, and distributing Docker containers. The Docker client and daemon communicate using a REST API, over UNIX sockets or a network interface.

### Key Docker Concepts
- **Image**: A read-only template with instructions for creating a Docker container. Images are built from a Dockerfile.
- **Container**: A runnable instance of an image. Containers are isolated from each other and the host machine.
- **Volume**: Persistent data storage that exists outside of the container's filesystem.
- **Network**: Docker creates virtual networks that allow containers to communicate with each other.
- **Registry**: A repository for Docker images. Docker Hub is the default public registry.

### Docker Commands
- `docker build -t myapp .` — Build an image from a Dockerfile
- `docker run -d -p 8080:80 myapp` — Run a container in detached mode
- `docker ps` — List running containers
- `docker logs <container>` — View container logs
- `docker exec -it <container> bash` — Execute a command in a running container
- `docker stop <container>` — Stop a running container
- `docker rm <container>` — Remove a container
- `docker images` — List images
- `docker rmi <image>` — Remove an image

## Dockerfile

A Dockerfile is a text document that contains all the commands a user could call on the command line to assemble an image. Using `docker build`, users can create an automated build that executes several command-line instructions in succession.

### Dockerfile Instructions
- `FROM` — Sets the base image for subsequent instructions
- `RUN` — Executes commands in a new layer on top of the current image
- `COPY` — Copies files from the build context into the image
- `ADD` — Similar to COPY but with additional features like URL support and tar extraction
- `WORKDIR` — Sets the working directory for subsequent instructions
- `ENV` — Sets environment variables
- `EXPOSE` — Documents which ports the container listens on
- `CMD` — Provides defaults for an executing container
- `ENTRYPOINT` — Configures a container to run as an executable
- `VOLUME` — Creates a mount point for persistent data
- `ARG` — Defines build-time variables
- `HEALTHCHECK` — Tells Docker how to test a container to check that it is still working

### Dockerfile Best Practices
- Use multi-stage builds to reduce image size
- Order instructions from least to most frequently changing for better caching
- Combine RUN commands to reduce layers
- Use .dockerignore to exclude unnecessary files
- Run as non-root user for security
- Use specific image tags instead of latest

## Docker Compose

Docker Compose is a tool for defining and running multi-container Docker applications. With Compose, you use a YAML file to configure your application's services, networks, and volumes. Then, with a single command, you create and start all the services from your configuration.

### Docker Compose File Structure
```yaml
version: '3.8'
services:
  web:
    build: .
    ports:
      - "8000:8000"
    depends_on:
      - db
    environment:
      - DATABASE_URL=postgresql://user:pass@db:5432/mydb
  db:
    image: postgres:15
    volumes:
      - db-data:/var/lib/postgresql/data
    environment:
      - POSTGRES_PASSWORD=pass
volumes:
  db-data:
networks:
  default:
    driver: bridge
```

### Docker Compose Commands
- `docker compose up -d --build` — Build and start services in detached mode
- `docker compose down` — Stop and remove containers
- `docker compose ps` — List running services
- `docker compose logs --tail=100` — View recent logs
- `docker compose restart <service>` — Restart a specific service
- `docker compose config -q` — Validate compose file silently

## APIs and FastAPI

An API (Application Programming Interface) is a set of rules and protocols that allows different software applications to communicate with each other. REST APIs use HTTP methods (GET, POST, PUT, DELETE) to perform operations on resources.

### FastAPI
FastAPI is a modern, high-performance web framework for building APIs with Python based on standard Python type hints. It provides automatic API documentation, data validation, and high performance comparable to NodeJS and Go.

### FastAPI Features
- Automatic interactive API documentation (Swagger UI and ReDoc)
- Data validation using Pydantic models
- Dependency injection system
- Async/await support for concurrent operations
- Automatic JSON serialization
- Path parameters, query parameters, and request bodies
- File uploads with UploadFile
- Static file serving
- Middleware support
- CORS configuration

### FastAPI Example
```python
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class Item(BaseModel):
    name: str
    price: float

@app.get("/health")
def health():
    return {"status": "healthy"}

@app.post("/items/")
def create_item(item: Item):
    return {"item": item, "status": "created"}
```

## Ports and Service Communication

In networked applications, ports are numerical identifiers that distinguish different services running on the same host. Each service listens on a specific port for incoming connections.

### Common Ports
- 80: HTTP
- 443: HTTPS
- 8000: Common development server port (FastAPI default)
- 8080: Alternative HTTP port
- 5432: PostgreSQL
- 6379: Redis
- 27017: MongoDB
- 9090: Prometheus
- 3000: Grafana
- 11434: Ollama

### Docker Port Mapping
In Docker, port mapping connects a port on the host machine to a port inside the container. The format is `host_port:container_port`. For example, `-p 8000:8000` maps host port 8000 to container port 8000. Inside Docker networks, containers can communicate using service names instead of localhost.

## RAG (Retrieval-Augmented Generation)

RAG is a technique that enhances LLM responses by retrieving relevant information from an external knowledge base before generating an answer. Instead of relying solely on the model's training data, RAG provides specific, up-to-date context.

### RAG Workflow
1. User asks a question
2. The question is converted to an embedding vector
3. The embedding is compared against stored document embeddings using vector similarity
4. The most similar chunks are retrieved as context
5. The retrieved context is combined with the question
6. The LLM generates an answer grounded in the retrieved context
7. The answer is returned along with source references and similarity scores

### RAG Benefits
- Provides up-to-date information beyond model training cutoff
- Grounds responses in specific, verifiable documents
- Reduces hallucination by providing factual context
- Allows domain-specific knowledge without fine-tuning
- Enables source attribution and evidence tracking

### RAG vs Non-RAG Comparison
- **With RAG**: Answers are grounded in retrieved documents, include source citations, have higher accuracy for domain-specific questions, but may have higher latency due to retrieval step
- **Without RAG**: Answers rely on model training knowledge, may hallucinate specific details, faster response time, better for general knowledge questions

## Chunking

Chunking is the process of breaking large documents into smaller, manageable pieces for embedding and retrieval. Effective chunking is crucial for RAG quality.

### Chunking Strategies
- **Fixed-size chunks**: Split text every N characters with optional overlap
- **Sentence-based chunks**: Split at sentence boundaries
- **Paragraph-based chunks**: Split at paragraph boundaries
- **Semantic chunks**: Split based on topic changes
- **Overlap**: Include a portion of the previous chunk to maintain context continuity

### Chunking Considerations
- Chunk size affects retrieval precision: smaller chunks are more precise but may lack context
- Larger chunks provide more context but may include irrelevant information
- Overlap helps maintain context across chunk boundaries
- Metadata (source, page number, chunk index) should be preserved with each chunk

## Embeddings

Embeddings are dense vector representations of text that capture semantic meaning. Similar texts have vectors that are close together in the embedding space.

### How Embeddings Work
- Text is processed by an embedding model (e.g., nomic-embed-text)
- The model outputs a fixed-dimensional vector (e.g., 768 dimensions)
- These vectors are stored in a vector database for later similarity search
- Query text is also converted to an embedding for comparison
- Similar embeddings indicate semantically similar content

### Embedding Models
- **nomic-embed-text**: A local embedding model suitable for document retrieval
- Embedding models are different from generation models — they create vector representations, not text
- The same embedding model must be used for both indexing and querying

## Cosine Similarity

Cosine similarity measures the cosine of the angle between two vectors. It ranges from -1 (opposite) to 1 (identical), with 0 indicating orthogonality (no similarity).

### Formula
cosine_similarity = (A · B) / (||A|| × ||B||)

### In RAG Applications
- ChromaDB uses cosine distance (1 - cosine_similarity) by default
- To convert: similarity = 1.0 - distance
- Higher similarity means more relevant content
- A typical threshold is 0.25 — chunks below this similarity may be filtered out
- Similarity is a proxy for relevance, not a guarantee of factual correctness

## ChromaDB

ChromaDB is an open-source vector database designed for AI applications. It stores embeddings along with metadata and supports efficient similarity search.

### ChromaDB Features
- Persistent storage with PersistentClient
- Collections for organizing different sets of embeddings
- Multiple distance functions: cosine, L2, inner product
- Metadata filtering for refined searches
- Batch operations for efficient indexing
- Simple Python API

### ChromaDB in This Project
- Collection: `devops_knowledge` with cosine similarity space
- Stores document chunks with metadata (source, page, chunk_index, document_id)
- Used by the retrieval service for semantic search
- Data persists across container restarts via Docker volumes

## Ingestion

Ingestion is the process of preparing and loading documents into the knowledge base. It involves extraction, normalization, chunking, embedding, and indexing.

### Ingestion Pipeline
1. **Extraction**: Read text from PDF, TXT, or MD files
2. **Normalization**: Clean and standardize text (collapse whitespace, strip)
3. **Chunking**: Split text into overlapping chunks (default: 500 chars, 50 overlap)
4. **Embedding**: Convert each chunk to a vector using nomic-embed-text
5. **Indexing**: Store chunks with embeddings and metadata in ChromaDB
6. **Metadata**: Preserve source filename, page number, chunk index, document ID

### Important Note
Uploading documents does NOT train or fine-tune the LLM. Documents are indexed for retrieval — the LLM uses them as context, not as training data.

## Ollama

Ollama is a tool for running large language models locally. It provides a simple API for model management and inference.

### Ollama Commands
- `ollama pull qwen2.5:3b` — Download a model
- `ollama list` — List available models
- `ollama run qwen2.5:3b` — Interactive chat with a model
- `ollama --version` — Check version
- `systemctl status ollama` — Check service status

### Ollama API
- `POST /api/generate` — Generate text completion
- `POST /api/embeddings` — Generate embeddings
- `GET /api/tags` — List available models
- Default port: 11434
- Set `OLLAMA_HOST=0.0.0.0:11434` for network access

### Model Management
- Use one generation model at a time to manage memory
- Set `OLLAMA_MAX_LOADED_MODELS=1` to limit memory usage
- Set `OLLAMA_KEEP_ALIVE=0` to unload models when not in use

## LLM Service

The LLM service manages communication with the selected language model through Ollama. It provides a generation endpoint that accepts questions, optional context, and model configuration.

### Service Responsibilities
- Model selection from available generation models
- Prompt construction (grounded for RAG, direct for non-RAG)
- Communication with Ollama API
- Response parsing and telemetry extraction
- Token counting and latency measurement

### Grounded Prompts
When RAG is enabled, the LLM receives a grounded prompt that includes retrieved context and instructions to:
- Use the provided context as primary evidence
- Not invent facts unsupported by the context
- Clearly state when insufficient information is available
- Reference sources when citing context

## Retrieval Service

The retrieval service handles embeddings, vector storage, and similarity search. It connects to ChromaDB for persistent storage and Ollama for embedding generation.

### Service Endpoints
- `GET /health` — Service health check
- `GET /stats` — Knowledge base statistics
- `GET /documents` — List all indexed documents
- `GET /retrieve?query=...&top_k=5` — Similarity search
- `POST /upsert` — Index a single chunk
- `POST /upsert_batch` — Index multiple chunks
- `POST /clear` — Clear all documents

## Orchestration

Orchestration coordinates multiple services to process a single user request through the complete pipeline. The FastAPI application serves as the orchestrator.

### Request Flow
1. User submits a question via the dashboard
2. The app validates input through guardrails
3. If RAG is enabled, the app queries the retrieval service for relevant chunks
4. Retrieved chunks are assembled into context
5. The context and question are sent to the LLM service
6. The LLM generates a grounded response
7. The app validates output through guardrails
8. The response, sources, and telemetry are returned to the user

## Monitoring and Observability

Monitoring involves collecting, processing, and visualizing metrics to understand system health and performance.

### Key Metrics
- **Latency**: Time taken for request processing
- **Token Usage**: Prompt and response token counts
- **Retrieval Similarity**: Quality of retrieved context
- **Error Rate**: Frequency of failed requests
- **Model Load Time**: Time to load models into memory
- **Generation Speed**: Tokens per second

## Troubleshooting

### Common Issues
- **App won't start**: Check Python imports, syntax errors, missing dependencies
- **Generation fails**: Verify Ollama is running, models are pulled, network is accessible
- **No retrieval results**: Check if knowledge base is seeded, verify embedding model
- **Upload not retrieved**: Check extraction, chunking, indexing pipeline
- **Slow generation**: Check CPU/RAM, model load times, context length

### Debug Commands
```bash
docker compose ps                    # Check service status
docker compose logs --tail=100       # View recent logs
curl http://localhost:8000/health    # Check app health
curl http://localhost:8001/health    # Check retrieval health
curl http://localhost:8002/health    # Check LLM health
curl http://localhost:8003/health    # Check ingestion health
```

## Security and Deployment

### Security Considerations
- Never expose internal services (retrieval, LLM, ingestion) directly to the internet
- Use Docker networks for service isolation
- The browser should only communicate with the app API, never directly with Ollama or other services
- Generated code must never be executed in the main application container — use the isolated code runner
- Input validation and guardrails prevent injection attacks
- The code runner is a classroom tool, not a production security boundary

### Deployment Best Practices
- Use environment variables for configuration (never hardcode secrets)
- Use Docker volumes for persistent data
- Implement health checks for all services
- Use `docker compose down` (not `down -v`) to preserve data
- Document all startup and shutdown procedures
