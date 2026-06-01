from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings

# Pass credentials separately to handle special characters in password
engine = create_async_engine(
    "postgresql+asyncpg://",
    connect_args={
        "host": "localhost",
        "port": 5432,
        "user": "cargo_user",
        "password": settings.DB_PASSWORD,
        "database": "cargo_db",
    },
    echo=settings.DEBUG,
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

class Base(DeclarativeBase):
    pass

async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise