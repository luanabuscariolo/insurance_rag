from datetime import datetime
from typing import Optional
from enum import StrEnum
from pydantic import BaseModel, Field

from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import Column, Integer, String, DateTime


# declarative base class
class Base(DeclarativeBase):
    pass

class ClaimDB(Base):
    __tablename__ = "claims"

    id = Column(Integer, primary_key=True, autoincrement=True)
    policy_number = Column(String(50), nullable=False, index=True)
    claimant_name = Column(String(50), nullable=False)
    claim_type = Column(String(50), nullable=False) #Enum: auto, home, health
    description = Column(String(255), nullable=False)
    amount_claimed = Column(Float, nullable=False)
    amount_approved = Column(Float, nullable=True)
    status = Column(String(30), nullable=False, default="pending") #Enum: pending, approved, rejected, in_review
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# Enums for claim type and status

class ClaimType(StrEnum):
    AUTO = "auto"
    HOME = "home"
    HEALTH = "health"

class ClaimStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    IN_REVIEW = "in_review"

# Pydantic schemas for claim request and response

class ClaimCreate(BaseModel):
    policy_number: str = Field(..., max_length=50)
    claimant_name: str = Field(..., max_length=50)
    claim_type: ClaimType = Field(...)
    description: str = Field(..., min_length=10, max_length=255)
    amount_claimed: float = Field(..., gt=0)

class ClaimUpdate(BaseModel):
    status: ClaimStatus = Field(...)
    amount_approved: Optional[float] = Field(None, gt=0)

class ClaimResponse(BaseModel):
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
    
    # Enable ORM mode to allow conversion from SQLAlchemy models
    model_config = {
        "from_attributes": True
    }

class ClaimListResponse(BaseModel):
    total: int
    items: list[ClaimResponse]