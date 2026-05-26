"""
Insurance Claims RAG API
========================
Sistema de gestão de sinistros com busca inteligente por linguagem natural.

Endpoints principais:
/claims         -CRUD de sinistros
/documents      -ingestão de apólices no índice vetorial
/search            -perguntas em linguagem natural (RAG)
/docs           -Swagger UI interativo
"""
from contextlib import asynccontextmanager

from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.database import init_db
from app.routes import claims, documents, search

from dotenv import load_dotenv

load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gerenciador de ciclo de vida da aplicação"""
    # Aqui você pode adicionar código de inicialização, como conexões de banco de dados
    print("Iniciando a aplicação...")
    Path("./data/policies").mkdir(parents=True, exist_ok=True)  # Criar pasta para dados se não existir
    Path("./data/chroma").mkdir(parents=True, exist_ok=True)

    await init_db()  # Inicializar o banco de dados

    print("Aplicação iniciada com sucesso!")
    print("Insurance RAG API pronta em http://localhost:8001")
    print("Swagger UI disponível em http://localhost:8001/docs")

    yield
    # Aqui você pode adicionar código de limpeza, como fechar conexões
    print("Encerrando a aplicação...")

app = FastAPI(
    title="Insurance Claims RAG API",
    description=(
        "API de gestão de sinistros com sistema RAG interativo. \n\n"
        "**Como começar:**\n"
        "1. `POST /documents/ingest/seed` — indexa os documentos de exemplo\n"
        "2. `POST /claims` — cria alguns sinistros\n"
        "3. `POST /search` — faz perguntas sobre as apólices\n"        
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(claims.router)
app.include_router(documents.router)
app.include_router(search.router)

@app.get("/", include_in_schema=False)
async def root():
    return JSONResponse({
        "message": "Insurance RAG API",
        "docs": "/docs",
        "health": "/health"
    })
