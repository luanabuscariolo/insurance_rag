from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import Column, Integer, String, DateTime


# declarative base class
class Base(DeclarativeBase):
    pass

class ClaimDB(Base):
    __tablename__ = "claims"

    id = Column(Integer, primary_key=True, autoincrement=True)
    policy_number = Column(String(50), nullable=False, index=True)
    fullname = Column(String, nullable=True)
    nickname = Column(String(64), nullable=True)
    create_date = Column(DateTime, server_default=func.now())
