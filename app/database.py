from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import text

from app.config import settings


def _fix_database_url(url: str) -> str:
    """
    Fix URL for asyncpg:
    - postgresql:// → postgresql+asyncpg://
    - Remove ?sslmode=require (asyncpg uses ssl= connect_args instead)
    """
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    # Remove sslmode param — asyncpg doesn't support it in the URL
    url = url.split("?")[0]
    return url


_db_url = _fix_database_url(settings.database_url)

engine = create_async_engine(
    _db_url,
    echo=False,
    connect_args={"ssl": True},
)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session


async def init_db():
    """Create tables and enable pgvector extension."""
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)
