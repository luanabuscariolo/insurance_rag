from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.models.claim import Base

# SQLite async — o arquivo fica em /data/insurance.db dentro do container
DATABASE_URL = "sqlite+aiosqlite:///./data/insurance.db"

engine = create_async_engine(
    DATABASE_URL,
    echo=False,         # muda para True para ver SQL no terminal
    connect_args={"check_same_thread": False},
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def init_db() -> None:
    """Cria as tabelas se não existirem."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db() -> AsyncSession:
    """Dependency injection — fornece sessão de banco para cada request."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
