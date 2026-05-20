from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.models.claim import Base

DATABASE_URL = "sqlite+aiosqlite:///./data/insurance.db"

# Create async engine and sessionmaker
engine = create_async_engine(
    DATABASE_URL,
    echo=True, 
    connect_args={"check_same_thread": False}
)

async_session = async_sessionmaker(
    bind=engine, 
    expire_on_commit=False, 
    class_=AsyncSession
)

async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def get_db() -> AsyncSession:
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

