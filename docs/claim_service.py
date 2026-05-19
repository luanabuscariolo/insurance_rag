from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.claim import ClaimCreate, ClaimDB, ClaimListResponse, ClaimResponse, ClaimStatus, ClaimUpdate


class ClaimService:
    """
    Camada de serviço — toda a lógica de negócio fica aqui.
    As rotas apenas chamam estes métodos.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── Create ────────────────────────────────────────────────────────────────

    async def create(self, payload: ClaimCreate) -> ClaimResponse:
        claim = ClaimDB(**payload.model_dump())
        self.db.add(claim)
        await self.db.flush()   # obtém o id gerado sem commit ainda
        await self.db.refresh(claim)
        return ClaimResponse.model_validate(claim)

    # ── Read ──────────────────────────────────────────────────────────────────

    async def get_by_id(self, claim_id: int) -> ClaimDB | None:
        result = await self.db.execute(select(ClaimDB).where(ClaimDB.id == claim_id))
        return result.scalar_one_or_none()

    async def list_claims(
        self,
        status: Optional[ClaimStatus] = None,
        claim_type: Optional[str] = None,
        policy_number: Optional[str] = None,
        skip: int = 0,
        limit: int = 20,
    ) -> ClaimListResponse:
        query = select(ClaimDB)

        # filtros opcionais
        if status:
            query = query.where(ClaimDB.status == status.value)
        if claim_type:
            query = query.where(ClaimDB.claim_type == claim_type)
        if policy_number:
            query = query.where(ClaimDB.policy_number == policy_number)

        # total para paginação
        count_result = await self.db.execute(select(func.count()).select_from(query.subquery()))
        total = count_result.scalar()

        # dados paginados
        result = await self.db.execute(query.offset(skip).limit(limit))
        items = [ClaimResponse.model_validate(c) for c in result.scalars().all()]

        return ClaimListResponse(total=total, items=items)

    # ── Update ────────────────────────────────────────────────────────────────

    async def update_status(self, claim_id: int, payload: ClaimUpdate) -> ClaimResponse | None:
        claim = await self.get_by_id(claim_id)
        if not claim:
            return None

        claim.status = payload.status.value
        if payload.amount_approved is not None:
            claim.amount_approved = payload.amount_approved

        await self.db.flush()
        await self.db.refresh(claim)
        return ClaimResponse.model_validate(claim)

    # ── Delete ────────────────────────────────────────────────────────────────

    async def delete(self, claim_id: int) -> bool:
        claim = await self.get_by_id(claim_id)
        if not claim:
            return False
        await self.db.delete(claim)
        return True

    # ── Stats (exemplo de query SQL mais avançada) ────────────────────────────

    async def get_stats(self) -> dict:
        """Estatísticas gerais dos sinistros — demonstra GROUP BY em SQL."""
        result = await self.db.execute(
            select(
                ClaimDB.status,
                func.count(ClaimDB.id).label("count"),
                func.sum(ClaimDB.amount_claimed).label("total_claimed"),
                func.avg(ClaimDB.amount_claimed).label("avg_claimed"),
            ).group_by(ClaimDB.status)
        )
        rows = result.all()
        return {
            "by_status": [
                {
                    "status": r.status,
                    "count": r.count,
                    "total_claimed": round(r.total_claimed or 0, 2),
                    "avg_claimed": round(r.avg_claimed or 0, 2),
                }
                for r in rows
            ]
        }
