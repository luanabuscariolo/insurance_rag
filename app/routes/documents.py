from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel
from pathlib import Path
from app.services.rag_service import RAGService

router = APIRouter(prefix="/documents", tags=["Documents"])

rag = RAGService()

class IngestTextRequest(BaseModel):
    content: str
    source_name: str
    policy_type: str = "general" #auto, home, health, general

@router.post("/ingest", summary="Indexar documento a partir de texto")
async def ingest_text(payload: IngestTextRequest) -> dict:
    """
    Recebe um texto, divide em chuncks, gera embeddings e armazena no ChronaDB.
    Use este endpoint para indexar conteúdo de apólices e manuais.
    """
    result = await rag.ingest_document(
        content=payload.content,
        source_name=payload.source_name,
        policy_type=payload.policy_type
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result

@router.post("/ingest/file", summary="Indexar documento via upload de arquivo.txt")
async def ingest_file(
    file: UploadFile = File(...),
    policy_type: str = "general"
) -> dict:
    """
    Faz upload de um arquivo .txt e o indexa automaticamente.
    """
    if not file.filename.endswith((".txt", ".md")):
        raise HTTPException(status_code=400, detail="Apenas arquivos .txt ou .md são aceitos")
    
    content_bytes = await file.read()
    try:
        content = content_bytes.decode("utf-8")
    except UnicodeDecodeError:
        content = content_bytes.decode("latin-1")

    result = await rag.ingest_document(
        content=content,
        source_name=file.filename,
        policy_type=policy_type,
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result

@router.post("/ingest/seed", summary="Indexar documentos de exemplo incluídos no projeto")
async def ingest_seed_data() -> dict:
    """
    Indexa os documentos de exemplo da pasta data/policies/.
    Útil para testar sem precisar fazer upload.
    """
    policies_dir = Path("./data/policies")
    if not policies_dir.exists():
        raise HTTPException(status_code=404, detail="Pasta data/policies não encontrada")

    txt_files = list(policies_dir.glob("*.txt"))
    if not txt_files:
        raise HTTPException(status_code=404, detail="Nenhum arquivo .txt encontrado em data/policies")

    results = []
    for file_path in txt_files:
        content = file_path.read_text(encoding="utf-8")

        # infere tipo pela convenção de nome
        name = file_path.stem.lower()
        if "auto" in name:
            policy_type = "auto"
        elif "home" in name or "residencial" in name:
            policy_type = "home"
        elif "health" in name or "saude" in name:
            policy_type = "health"
        else:
            policy_type = "general"

        result = await rag.ingest_document(
            content=content,
            source_name=file_path.name,
            policy_type=policy_type,
        )
        results.append(result)

    return {"seeded": len(results), "details": results}


@router.get("/stats", summary="Estatísticas do índice vetorial")
async def get_collection_stats() -> dict:
    return rag.collection_stats()
