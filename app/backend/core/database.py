from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlmodel.ext.asyncio.session import AsyncSession

import app.backend.core.db_logging  # noqa: F401 — side effect: registers query-logging listeners
from app.backend.core.config import settings

engine = create_async_engine(settings.DATABASE_URL, echo=settings.ENV == "dev")

AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session
