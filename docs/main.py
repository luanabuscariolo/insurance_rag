"""
Insurance Claims RAG API
========================
Sistema de gestão de sinistros com busca inteligente por linguagem natural.

Endpoints principais:
  /claims        — CRUD de sinistros
  /documents     — ingestão de apólices no índice vetorial
  /ask           — perguntas em linguagem natural (RAG)
  /docs          — Swagger UI interativo
"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.database import init_db
from app.routes import claims, documents, search


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Executado na inicialização e no encerramento da aplicação."""
    # garante que as pastas de dados existam
    Path("./data/policies").mkdir(parents=True, exist_ok=True)
    Path("./data/chroma").mkdir(parents=True, exist_ok=True)

    # cria as tabelas SQL se não existirem
    await init_db()

    print("✅ Banco de dados inicializado")
    print("✅ Insurance RAG API pronta em http://localhost:8000")
    print("📖 Swagger UI: http://localhost:8000/docs")

    yield  # a aplicação fica viva aqui

    print("🛑 Encerrando aplicação...")


# ── Criação da app ────────────────────────────────────────────────────────────

app = FastAPI(
    title="Insurance Claims RAG API",
    description=(
        "API de gestão de sinistros com sistema RAG integrado.\n\n"
        "**Como começar:**\n"
        "1. `POST /documents/ingest/seed` — indexa os documentos de exemplo\n"
        "2. `POST /claims` — cria alguns sinistros\n"
        "3. `POST /ask` — faz perguntas sobre as apólices\n"
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — permite chamadas do navegador em desenvolvimento
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────

app.include_router(claims.router)
app.include_router(documents.router)
app.include_router(search.router)


# ── Health check ──────────────────────────────────────────────────────────────

@app.get("/health", tags=["Sistema"])
async def health_check() -> JSONResponse:
    return JSONResponse({"status": "ok", "service": "insurance-rag-api"})


@app.get("/", include_in_schema=False)
async def root():
    return JSONResponse({
        "message": "Insurance RAG API",
        "docs": "/docs",
        "health": "/health",
    })
