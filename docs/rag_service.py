"""
RAG Service — coração do sistema.

Pipeline completo:
  Documento → chunks → embeddings → ChromaDB
  Pergunta   → embedding → busca vetorial → contexto → LLM → resposta

Usa sentence-transformers por padrão (gratuito, sem API key).
OpenAI é opcional e ativado via variável de ambiente.
"""

import os
import re
import uuid
from pathlib import Path
from typing import Optional

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer

# ── Configuração ──────────────────────────────────────────────────────────────

CHROMA_PATH = "./data/chroma"
EMBED_MODEL = "all-MiniLM-L6-v2"   # rápido, leve, bom para PT/EN
CHUNK_SIZE = 500                     # caracteres por chunk
CHUNK_OVERLAP = 80                   # sobreposição entre chunks
TOP_K = 4                            # quantos chunks recuperar por query
COLLECTION_NAME = "insurance_policies"

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")


# ── RAG Service ───────────────────────────────────────────────────────────────

class RAGService:
    """
    Serviço responsável por:
    1. Ingestão de documentos (chunking + embeddings + armazenamento)
    2. Retrieval (busca vetorial por similaridade)
    3. Geração de respostas com contexto (usando OpenAI se configurado)
    """

    def __init__(self) -> None:
        # modelo de embedding (carrega uma vez, fica em memória)
        self._embedder = SentenceTransformer(EMBED_MODEL)

        # cliente ChromaDB persistente em disco
        Path(CHROMA_PATH).mkdir(parents=True, exist_ok=True)
        self._chroma = chromadb.PersistentClient(
            path=CHROMA_PATH,
            settings=Settings(anonymized_telemetry=False),
        )
        self._collection = self._chroma.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},  # similaridade por cosseno
        )

    # ── 1. CHUNKING ───────────────────────────────────────────────────────────

    def _split_into_chunks(self, text: str) -> list[str]:
        """
        Divide o texto em chunks com overlap.

        Por que overlap? Para que uma informação no final de um chunk
        também apareça no início do próximo — evita perder contexto
        em divisões ruins.
        """
        text = re.sub(r"\s+", " ", text).strip()  # normaliza espaços
        chunks = []
        start = 0

        while start < len(text):
            end = start + CHUNK_SIZE
            chunk = text[start:end]

            # tenta terminar no fim de uma frase
            last_period = max(chunk.rfind(". "), chunk.rfind(".\n"), chunk.rfind("! "))
            if last_period > CHUNK_SIZE * 0.5:
                end = start + last_period + 1
                chunk = text[start:end]

            chunks.append(chunk.strip())
            start = end - CHUNK_OVERLAP  # overlap para próximo chunk

        return [c for c in chunks if len(c) > 50]  # remove chunks muito pequenos

    # ── 2. EMBEDDING ─────────────────────────────────────────────────────────

    def _embed(self, texts: list[str]) -> list[list[float]]:
        """Converte textos em vetores numéricos."""
        return self._embedder.encode(texts, show_progress_bar=False).tolist()

    # ── 3. INGESTÃO ───────────────────────────────────────────────────────────

    async def ingest_document(
        self,
        content: str,
        source_name: str,
        policy_type: str = "general",
    ) -> dict:
        """
        Processa um documento e armazena no ChromaDB.

        Args:
            content: texto completo do documento
            source_name: nome do arquivo ou identificador
            policy_type: categoria (auto, home, health)

        Returns:
            dict com estatísticas da ingestão
        """
        chunks = self._split_into_chunks(content)
        if not chunks:
            return {"error": "Documento vazio ou muito curto", "chunks": 0}

        embeddings = self._embed(chunks)

        ids = [f"{source_name}_{i}_{uuid.uuid4().hex[:8]}" for i in range(len(chunks))]
        metadatas = [
            {"source": source_name, "policy_type": policy_type, "chunk_index": i}
            for i in range(len(chunks))
        ]

        self._collection.add(
            documents=chunks,
            embeddings=embeddings,
            metadatas=metadatas,
            ids=ids,
        )

        return {
            "source": source_name,
            "policy_type": policy_type,
            "chunks_created": len(chunks),
            "total_chars": len(content),
        }

    # ── 4. RETRIEVAL ──────────────────────────────────────────────────────────

    def retrieve(self, query: str, policy_type: Optional[str] = None, n_results: int = TOP_K) -> list[dict]:
        """
        Busca os chunks mais relevantes para a pergunta.

        O ChromaDB compara o embedding da query com todos os
        embeddings armazenados e devolve os mais próximos.
        """
        query_embedding = self._embed([query])

        where_filter = {"policy_type": policy_type} if policy_type else None

        results = self._collection.query(
            query_embeddings=query_embedding,
            n_results=min(n_results, self._collection.count() or 1),
            where=where_filter,
            include=["documents", "metadatas", "distances"],
        )

        chunks = []
        for doc, meta, dist in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        ):
            chunks.append({
                "content": doc,
                "source": meta.get("source", "unknown"),
                "policy_type": meta.get("policy_type", "general"),
                "relevance_score": round(1 - dist, 4),  # cosseno: 1 = idêntico
            })

        return chunks

    # ── 5. GERAÇÃO ────────────────────────────────────────────────────────────

    async def answer(self, question: str, policy_type: Optional[str] = None) -> dict:
        """
        Pipeline RAG completo:
        1. Recupera chunks relevantes
        2. Constrói contexto
        3. Chama LLM (OpenAI se configurado, senão devolve contexto bruto)
        """
        retrieved_chunks = self.retrieve(question, policy_type)

        if not retrieved_chunks:
            return {
                "question": question,
                "answer": "Nenhum documento indexado encontrado. Use POST /documents/ingest primeiro.",
                "sources": [],
            }

        context = "\n\n---\n\n".join(
            f"[Fonte: {c['source']}]\n{c['content']}" for c in retrieved_chunks
        )

        # com OpenAI configurado
        if OPENAI_API_KEY:
            answer_text = await self._generate_with_openai(question, context)
        else:
            # sem API key: devolve contexto recuperado (útil para testar sem custo)
            answer_text = (
                "⚠️ OPENAI_API_KEY não configurada — devolvendo contexto recuperado:\n\n"
                + context
            )

        return {
            "question": question,
            "answer": answer_text,
            "sources": [
                {"source": c["source"], "relevance": c["relevance_score"]}
                for c in retrieved_chunks
            ],
        }

    async def _generate_with_openai(self, question: str, context: str) -> str:
        """Chama a OpenAI com o contexto recuperado pelo RAG."""
        try:
            from openai import AsyncOpenAI

            client = AsyncOpenAI(api_key=OPENAI_API_KEY)
            response = await client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Você é um assistente especializado em seguros. "
                            "Responda APENAS com base no contexto fornecido. "
                            "Se a resposta não estiver no contexto, diga claramente que não encontrou a informação. "
                            "Seja preciso, objetivo e cite a fonte quando relevante.\n\n"
                            f"CONTEXTO:\n{context}"
                        ),
                    },
                    {"role": "user", "content": question},
                ],
                temperature=0.1,   # baixo para respostas mais factuais
                max_tokens=600,
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Erro ao chamar OpenAI: {e}\n\nContexto recuperado:\n{context}"

    # ── Utilitários ───────────────────────────────────────────────────────────

    def collection_stats(self) -> dict:
        """Informações sobre o que está indexado."""
        count = self._collection.count()
        return {
            "total_chunks": count,
            "collection": COLLECTION_NAME,
            "embed_model": EMBED_MODEL,
        }
