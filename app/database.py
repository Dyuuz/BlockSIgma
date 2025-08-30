import os
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

load_dotenv()

DB_USER = os.getenv("DATABASE_USER")
DB_PASS = os.getenv("DATABASE_PASSWORD")
DB_HOST = os.getenv("DATABASE_SERVER")
DB_PORT = os.getenv("DATABASE_PORT")
DB_NAME = os.getenv("DATABASE_NAME")

# build async URL
DATABASE_URL = (
    f"postgresql+asyncpg://{DB_USER}:{DB_PASS}"
    f"@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

# create async engine
engine: AsyncEngine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_size=10,
)

# AsyncSession factory
AsyncSessionLocal = sessionmaker(
    bind=engine,
    expire_on_commit=False,
    class_=AsyncSession
)

# Base class for models
Base = declarative_base()
from sqlalchemy import text
async def init_db():
    """Initializes the database by creating tables if they don't exist."""
    async with engine.begin() as conn:
        # await conn.execute(text("ALTER TABLE binanceprice ADD COLUMN last_updated TIMESTAMP"))
        await conn.run_sync(Base.metadata.create_all)
    print("Database tables created/checked.")


# Dependency to get DB session
async def get_db():
    """
    Yield an AsyncSession, closing it after use.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
            
            

