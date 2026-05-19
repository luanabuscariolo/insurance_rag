# 🏥 Insurance Claims RAG API

Sistema de gestão de sinistros com busca inteligente por linguagem natural.

Combina **FastAPI** + **SQLite** + **ChromaDB** + **Sentence Transformers** num pipeline RAG completo, dockerizado e pronto para produção.

---

## O que este projeto faz

| Funcionalidade | Tecnologia |
|---|---|
| CRUD de sinistros com filtros e paginação | FastAPI + SQLAlchemy + SQLite |
| Ingestão de documentos de apólices | Chunking + Sentence Transformers |
| Busca semântica por similaridade | ChromaDB (vector database) |
| Perguntas em linguagem natural | RAG pipeline + OpenAI (opcional) |
| Deploy em container | Docker + docker-compose |

---

## Arquitetura

```
┌─────────────────────────────────────────────────────────────┐
│                        FastAPI App                          │
├──────────────┬──────────────────┬───────────────────────────┤
│  /claims     │  /documents      │  /ask                     │
│  CRUD        │  Ingestão RAG    │  Perguntas linguagem nat. │
├──────────────┼──────────────────┼───────────────────────────┤
│ ClaimService │  RAGService      │  RAGService               │
├──────────────┼──────────────────┴───────────────────────────┤
│  SQLite      │         ChromaDB (vector store)              │
│  (sinistros) │  + Sentence Transformers (embeddings)        │
└──────────────┴──────────────────────────────────────────────┘
```

### Pipeline RAG explicado

```
INGESTÃO:
  Documento .txt
      │
      ▼
  Chunking (500 chars, 80 overlap)
      │
      ▼
  Embeddings (all-MiniLM-L6-v2)
      │
      ▼
  ChromaDB (persiste em disco)

QUERY:
  Pergunta do usuário
      │
      ▼
  Embedding da pergunta
      │
      ▼
  Busca por similaridade de cosseno no ChromaDB
      │
      ▼
  Top-4 chunks mais relevantes
      │
      ▼
  Prompt: "Responda com base neste contexto: [chunks]"
      │
      ▼
  OpenAI gpt-4o-mini → Resposta final
```

---

## Estrutura de pastas

```
insurance-rag/
├── app/
│   ├── main.py              # FastAPI app, lifespan, routers
│   ├── database.py          # engine SQLAlchemy async, get_db
│   ├── models/
│   │   └── claim.py         # SQLAlchemy ORM + Pydantic schemas
│   ├── services/
│   │   ├── claim_service.py # lógica de negócio dos sinistros
│   │   └── rag_service.py   # chunking, embeddings, retrieval, geração
│   └── routes/
│       ├── claims.py        # endpoints CRUD
│       ├── documents.py     # endpoints de ingestão
│       └── search.py        # endpoint /ask (RAG)
├── data/
│   └── policies/            # documentos .txt de apólices
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example
└── README.md
```

---

## Como rodar

### Opção 1 — Docker (recomendado)

```bash
# 1. Clone o repositório
git clone https://github.com/seu-usuario/insurance-rag.git
cd insurance-rag

# 2. Copie e configure variáveis de ambiente
cp .env.example .env
# edite .env e adicione sua OPENAI_API_KEY (opcional)

# 3. Suba os containers
docker compose up --build

# 4. Acesse o Swagger UI
# http://localhost:8000/docs
```

### Opção 2 — Local (sem Docker)

```bash
# 1. Crie e ative o ambiente virtual
python -m venv .venv
source .venv/bin/activate        # Linux/Mac
# ou: .venv\Scripts\activate     # Windows

# 2. Instale as dependências
pip install -r requirements.txt

# 3. Configure as variáveis
cp .env.example .env

# 4. Crie as pastas de dados
mkdir -p data/policies data/chroma

# 5. Inicie a API
uvicorn app.main:app --reload --port 8000

# 6. Acesse: http://localhost:8000/docs
```

---

## Testando o sistema

### Passo 1 — Indexar os documentos de exemplo

```bash
curl -X POST http://localhost:8000/documents/ingest/seed
```

Resposta esperada:
```json
{
  "seeded": 3,
  "details": [
    {"source": "policy_auto.txt", "chunks_created": 14, ...},
    {"source": "policy_home.txt", "chunks_created": 16, ...},
    {"source": "policy_health.txt", "chunks_created": 18, ...}
  ]
}
```

### Passo 2 — Criar um sinistro

```bash
curl -X POST http://localhost:8000/claims \
  -H "Content-Type: application/json" \
  -d '{
    "policy_number": "POL-2024-001",
    "claimant_name": "Maria Silva",
    "claim_type": "auto",
    "description": "Colisão traseira na Av. Paulista, danos na traseira do veículo",
    "amount_claimed": 8500.00
  }'
```

### Passo 3 — Fazer uma pergunta (RAG)

```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Qual o prazo para comunicar um sinistro de colisão?",
    "policy_type": "auto"
  }'
```

Resposta:
```json
{
  "question": "Qual o prazo para comunicar um sinistro de colisão?",
  "answer": "De acordo com a apólice de seguro automóvel, o segurado tem prazo de até 72 horas após o sinistro para comunicar à seguradora. Em casos de roubo ou furto, o prazo é reduzido para 48 horas.",
  "sources": [
    {"source": "policy_auto.txt", "relevance": 0.891}
  ]
}
```

### Passo 4 — Listar sinistros com filtro

```bash
# todos os sinistros
curl http://localhost:8000/claims

# filtrado por status
curl "http://localhost:8000/claims?status=pending&claim_type=auto"

# estatísticas agrupadas
curl http://localhost:8000/claims/stats/summary
```

### Passo 5 — Atualizar status de um sinistro

```bash
curl -X PATCH http://localhost:8000/claims/1/status \
  -H "Content-Type: application/json" \
  -d '{"status": "approved", "amount_approved": 7200.00}'
```

---

## Endpoints

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/health` | Status da API |
| POST | `/claims` | Criar sinistro |
| GET | `/claims` | Listar (com filtros) |
| GET | `/claims/{id}` | Buscar por ID |
| PATCH | `/claims/{id}/status` | Atualizar status |
| DELETE | `/claims/{id}` | Remover |
| GET | `/claims/stats/summary` | Estatísticas SQL |
| POST | `/documents/ingest` | Indexar texto |
| POST | `/documents/ingest/file` | Upload de .txt |
| POST | `/documents/ingest/seed` | Indexar exemplos |
| GET | `/documents/stats` | Info do índice vetorial |
| POST | `/ask` | Pergunta RAG completa |
| GET | `/ask/retrieve` | Só retrieval (debug) |

---

## Conceitos aplicados neste projeto

- **RAG (Retrieval Augmented Generation)**: recupera contexto relevante antes de gerar resposta
- **Chunking com overlap**: divide documentos mantendo contexto nas bordas
- **Embeddings semânticos**: representação vetorial do significado do texto
- **Vector database**: busca por similaridade em vez de palavras-chave exactas
- **Async Python**: todas as operações I/O são assíncronas (async/await)
- **Dependency Injection**: FastAPI injeta sessão de DB em cada request
- **Separação de responsabilidades**: routes → services → models
- **Pydantic v2**: validação e serialização de dados
- **SQLAlchemy async**: ORM moderno com suporte a asyncio

---

## Próximos passos (evoluções possíveis)

- [ ] Adicionar autenticação (JWT)
- [ ] Reranking dos chunks recuperados
- [ ] Hybrid search (vetorial + BM25 por palavras-chave)
- [ ] Migrar para PostgreSQL + pgvector em produção
- [ ] Observabilidade com LangSmith ou Phoenix Arize
- [ ] Suporte a PDF (extração com pypdf)
- [ ] Testes unitários com pytest

---

## Tecnologias usadas

- **FastAPI** — framework web async
- **SQLAlchemy** — ORM async com SQLite
- **ChromaDB** — vector database local
- **Sentence Transformers** — embeddings gratuitos (all-MiniLM-L6-v2)
- **OpenAI** — geração de respostas (opcional)
- **Pydantic v2** — validação de dados
- **Docker** — containerização
