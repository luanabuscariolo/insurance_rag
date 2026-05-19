from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field
from sqlalchemy import Column, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase


# ── SQLAlchemy base ──────────────────────────────────────────────────────────

class Base(DeclarativeBase):
    pass


class ClaimDB(Base):
    """Tabela de sinistros no banco de dados."""

    __tablename__ = "claims"

    id = Column(Integer, primary_key=True, autoincrement=True)
    policy_number = Column(String(50), nullable=False, index=True)
    claimant_name = Column(String(100), nullable=False)
    claim_type = Column(String(50), nullable=False)     # auto, home, health
    description = Column(Text, nullable=False)
    amount_claimed = Column(Float, nullable=False)
    amount_approved = Column(Float, nullable=True)
    status = Column(String(30), nullable=False, default="pending")  # pending, approved, rejected, in_review
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ── Enums ─────────────────────────────────────────────────────────────────────

class ClaimType(str, Enum):
    auto = "auto"
    home = "home"
    health = "health"


class ClaimStatus(str, Enum):
    pending = "pending"
    in_review = "in_review"
    approved = "approved"
    rejected = "rejected"


# ── Pydantic schemas (request / response) ────────────────────────────────────

class ClaimCreate(BaseModel):
    """Payload para criar novo sinistro."""

    policy_number: str = Field(..., min_length=3, max_length=50, example="POL-2024-001")
    claimant_name: str = Field(..., min_length=2, max_length=100, example="Maria Silva")
    claim_type: ClaimType = Field(..., example="auto")
    description: str = Field(..., min_length=10, example="Colisão traseira na Av. Paulista")
    amount_claimed: float = Field(..., gt=0, example=8500.00)


class ClaimUpdate(BaseModel):
    """Payload para atualizar status e valor aprovado."""

    status: ClaimStatus
    amount_approved: Optional[float] = Field(None, ge=0)


class ClaimResponse(BaseModel):
    """Resposta completa de um sinistro."""

    id: int
    policy_number: str
    claimant_name: str
    claim_type: ClaimType
    description: str
    amount_claimed: float
    amount_approved: Optional[float]
    status: ClaimStatus
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ClaimListResponse(BaseModel):
    total: int
    items: list[ClaimResponse]
