from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

from app.services.rag_service import RAGService

router = APIRouter(prefix="/ask", tags=["RAG — Perguntas"])

rag = RAGService()


class QuestionRequest(BaseModel):
    question: str
    policy_type: Optional[str] = None   # auto, home, health, None = todos


class QuestionResponse(BaseModel):
    question: str
    answer: str
    sources: list[dict]


# ── POST /ask ─────────────────────────────────────────────────────────────────

@router.post(
    "",
    response_model=QuestionResponse,
    summary="Fazer pergunta em linguagem natural sobre as apólices indexadas",
)
async def ask_question(payload: QuestionRequest) -> QuestionResponse:
    """
    Pipeline RAG completo:

    1. Converte a pergunta em embedding
    2. Busca os trechos mais relevantes no ChromaDB
    3. Envia contexto + pergunta ao LLM (OpenAI se configurado)
    4. Retorna resposta e fontes utilizadas

    **Exemplo de perguntas:**
    - "Qual o prazo para acionar o seguro auto após um sinistro?"
    - "O seguro residencial cobre danos por enchente?"
    - "Quais documentos preciso para acionar o seguro saúde?"
    """
    result = await rag.answer(
        question=payload.question,
        policy_type=payload.policy_type,
    )
    return QuestionResponse(**result)


# ── GET /ask/retrieve ─────────────────────────────────────────────────────────

@router.get("/retrieve", summary="Apenas recuperar chunks sem gerar resposta (debug)")
async def retrieve_only(
    q: str,
    policy_type: Optional[str] = None,
    n: int = 4,
) -> dict:
    """
    Útil para debugar o retrieval sem gastar tokens de LLM.
    Mostra exatamente o que seria enviado como contexto.
    """
    chunks = rag.retrieve(q, policy_type, n)
    return {"query": q, "chunks_retrieved": len(chunks), "chunks": chunks}
