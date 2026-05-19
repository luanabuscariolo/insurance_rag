from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.claim import ClaimCreate, ClaimListResponse, ClaimResponse, ClaimStatus, ClaimUpdate
from app.services.claim_service import ClaimService

router = APIRouter(prefix="/claims", tags=["Claims"])


def get_service(db: AsyncSession = Depends(get_db)) -> ClaimService:
    """Dependency: injeta o serviço com a sessão de banco."""
    return ClaimService(db)


# ── POST /claims ──────────────────────────────────────────────────────────────

@router.post(
    "",
    response_model=ClaimResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Criar novo sinistro",
)
async def create_claim(
    payload: ClaimCreate,
    service: ClaimService = Depends(get_service),
) -> ClaimResponse:
    return await service.create(payload)


# ── GET /claims ───────────────────────────────────────────────────────────────

@router.get(
    "",
    response_model=ClaimListResponse,
    summary="Listar sinistros com filtros opcionais",
)
async def list_claims(
    status: Optional[ClaimStatus] = Query(None, description="Filtrar por status"),
    claim_type: Optional[str] = Query(None, description="Filtrar por tipo: auto, home, health"),
    policy_number: Optional[str] = Query(None, description="Filtrar por número da apólice"),
    skip: int = Query(0, ge=0, description="Paginação: registros a pular"),
    limit: int = Query(20, ge=1, le=100, description="Paginação: máximo de registros"),
    service: ClaimService = Depends(get_service),
) -> ClaimListResponse:
    return await service.list_claims(status, claim_type, policy_number, skip, limit)


# ── GET /claims/{id} ──────────────────────────────────────────────────────────

@router.get(
    "/{claim_id}",
    response_model=ClaimResponse,
    summary="Buscar sinistro por ID",
)
async def get_claim(
    claim_id: int,
    service: ClaimService = Depends(get_service),
) -> ClaimResponse:
    claim = await service.get_by_id(claim_id)
    if not claim:
        raise HTTPException(status_code=404, detail=f"Sinistro {claim_id} não encontrado")
    from app.models.claim import ClaimResponse
    return ClaimResponse.model_validate(claim)


# ── PATCH /claims/{id}/status ─────────────────────────────────────────────────

@router.patch(
    "/{claim_id}/status",
    response_model=ClaimResponse,
    summary="Atualizar status e valor aprovado",
)
async def update_claim_status(
    claim_id: int,
    payload: ClaimUpdate,
    service: ClaimService = Depends(get_service),
) -> ClaimResponse:
    result = await service.update_status(claim_id, payload)
    if not result:
        raise HTTPException(status_code=404, detail=f"Sinistro {claim_id} não encontrado")
    return result


# ── DELETE /claims/{id} ───────────────────────────────────────────────────────

@router.delete(
    "/{claim_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remover sinistro",
)
async def delete_claim(
    claim_id: int,
    service: ClaimService = Depends(get_service),
) -> None:
    deleted = await service.delete(claim_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Sinistro {claim_id} não encontrado")


# ── GET /claims/stats/summary ─────────────────────────────────────────────────

@router.get(
    "/stats/summary",
    summary="Estatísticas agrupadas por status",
)
async def get_stats(service: ClaimService = Depends(get_service)) -> dict:
    return await service.get_stats()
