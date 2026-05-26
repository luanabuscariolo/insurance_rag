![Status](https://img.shields.io/badge/status-active-brightgreen)
![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.136-009688)
![License](https://img.shields.io/badge/license-MIT-green)

# Insurance Claims RAG API

A REST API for insurance claims management with natural language search, built on a full RAG (Retrieval-Augmented Generation) pipeline.

Combines **FastAPI** + **SQLite** + **ChromaDB** + **Sentence Transformers** for semantic retrieval, with optional answer generation via **LM Studio** (local) or any OpenAI-compatible backend.

---

## Features

| Feature | Technology |
|---|---|
| Claims CRUD with filters and pagination | FastAPI + SQLAlchemy + SQLite |
| Policy document ingestion | Chunking + Sentence Transformers |
| Semantic similarity search | ChromaDB (vector database) |
| Natural language Q&A | RAG pipeline + LM Studio / OpenAI-compatible |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        FastAPI App                          │
├──────────────┬──────────────────┬───────────────────────────┤
│  /claims     │  /documents      │  /ask                     │
│  CRUD        │  Document ingest │  Natural language Q&A     │
├──────────────┼──────────────────┼───────────────────────────┤
│ ClaimService │              RAGService                      │
├──────────────┼──────────────────┴───────────────────────────┤
│  SQLite      │  ChromaDB (vector store)                     │
│  (claims)    │  + Sentence Transformers (embeddings)        │
└──────────────┴──────────────────────────────────────────────┘
```

### RAG Pipeline

```
INGESTION:
  .txt / .md document
      │
      ▼
  Chunking (500 chars, 80 overlap)
      │
      ▼
  Embeddings (all-MiniLM-L6-v2)
      │
      ▼
  ChromaDB (persisted to disk)

QUERY:
  User question
      │
      ▼
  Question embedding
      │
      ▼
  Cosine similarity search in ChromaDB
      │
      ▼
  Top-4 most relevant chunks
      │
      ▼
  Prompt: "Answer based on this context: [chunks]"
      │
      ▼
  LM Studio / OpenAI-compatible LLM → Final answer
```

---

## Project Structure

```
insurance-rag/
├── app/
│   ├── main.py              # FastAPI app, lifespan, routers
│   ├── database.py          # Async SQLAlchemy engine
│   ├── models/
│   │   └── claim.py         # SQLAlchemy ORM + Pydantic schemas
│   ├── services/
│   │   ├── claim_service.py # Claims business logic
│   │   └── rag_service.py   # Chunking, embeddings, retrieval, generation
│   └── routes/
│       ├── claims.py        # CRUD endpoints
│       ├── documents.py     # Document ingestion endpoints
│       └── search.py        # /ask RAG endpoint
├── data/
│   └── policies/            # Sample .txt policy documents
├── requirements.txt
└── README.md
```

---

## Getting Started

### Prerequisites

- Python 3.11+
- (Optional) [LM Studio](https://lmstudio.ai/) for local LLM answer generation

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/your-username/insurance-rag.git
cd insurance-rag

# 2. Create and activate virtual environment
python -m venv .venv
.venv\Scripts\activate          # Windows
# or: source .venv/bin/activate  # Linux/Mac

# 3. Install dependencies
pip install -r requirements.txt

# 4. Start the API
uvicorn app.main:app --reload --port 8000
```

Open **http://localhost:8000/docs** for the interactive Swagger UI.

### LM Studio (Optional)

To enable local LLM answer generation:

1. Download and install [LM Studio](https://lmstudio.ai/)
2. Load a chat model (e.g. `Mistral 7B`, `Llama 3`)
3. Start the local server (default: `http://localhost:1234`)
4. Set the following environment variables before starting the API:

```env
OPENAI_API_KEY=lm-studio
OPENAI_BASE_URL=http://localhost:1234/v1
OPENAI_MODEL=<your-loaded-model-name>
```

> Without LM Studio configured, `/ask` still works — it returns the raw retrieved context chunks instead of a generated answer.

---

## Usage

### Step 1 — Index sample documents

```bash
curl -X POST http://localhost:8000/documents/ingest/seed
```

```json
{
  "seeded": 3,
  "details": [
    {"source": "auto_policy.txt", "chunks_created": 14},
    {"source": "home_policy.txt", "chunks_created": 16},
    {"source": "health_policy.txt", "chunks_created": 18}
  ]
}
```

### Step 2 — Create a claim

```bash
curl -X POST http://localhost:8000/claims \
  -H "Content-Type: application/json" \
  -d '{
    "policy_number": "POL-2024-001",
    "claimant_name": "Jane Smith",
    "claim_type": "auto",
    "description": "Rear-end collision, damage to rear bumper",
    "amount_claimed": 8500.00
  }'
```

### Step 3 — Ask a question (RAG)

```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What is the deadline to report a collision claim?",
    "policy_type": "auto"
  }'
```

```json
{
  "question": "What is the deadline to report a collision claim?",
  "answer": "According to the auto insurance policy, the insured must report a claim within 72 hours of the incident...",
  "sources": [
    {"source": "auto_policy.txt", "relevance": 0.891}
  ]
}
```

### Step 4 — List claims with filters

```bash
curl http://localhost:8000/claims
curl "http://localhost:8000/claims?status=pending&claim_type=auto"
curl http://localhost:8000/claims/stats/summary
```

### Step 5 — Update claim status

```bash
curl -X PATCH http://localhost:8000/claims/1/status \
  -H "Content-Type: application/json" \
  -d '{"status": "approved", "amount_approved": 7200.00}'
```

---

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | API health check |
| POST | `/claims` | Create a claim |
| GET | `/claims` | List claims (with filters) |
| GET | `/claims/{id}` | Get claim by ID |
| PATCH | `/claims/{id}/status` | Update claim status |
| DELETE | `/claims/{id}` | Delete a claim |
| GET | `/claims/stats/summary` | Aggregated statistics |
| POST | `/documents/ingest` | Index raw text |
| POST | `/documents/ingest/file` | Upload a .txt or .md file |
| POST | `/documents/ingest/seed` | Index sample policies |
| GET | `/documents/stats` | Vector index info |
| POST | `/ask` | Full RAG Q&A |
| GET | `/ask/retrieve` | Retrieval only (debug) |

---

## Tech Stack

| Layer | Technology |
|---|---|
| Web framework | FastAPI (async) |
| ORM / Database | SQLAlchemy async + SQLite |
| Vector store | ChromaDB |
| Embeddings | Sentence Transformers (`all-MiniLM-L6-v2`) |
| LLM backend | LM Studio (local) / any OpenAI-compatible API |
| Data validation | Pydantic v2 |

---

## Key Concepts

- **RAG**: retrieves relevant context before generating an answer
- **Chunking with overlap**: splits documents while preserving context at boundaries
- **Semantic embeddings**: vector representations of text meaning
- **Vector database**: similarity search instead of exact keyword matching
- **Async Python**: all I/O operations use `async/await`
- **Dependency injection**: FastAPI injects DB session per request
- **Separation of concerns**: routes → services → models

---

## Roadmap

- [ ] JWT authentication
- [ ] Chunk reranking
- [ ] Hybrid search (vector + BM25)
- [ ] PostgreSQL + pgvector migration
- [ ] PDF support (pypdf)
- [ ] Unit tests (pytest)
- [ ] Docker support
