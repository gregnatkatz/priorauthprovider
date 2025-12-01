from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = "sqlite+aiosqlite:///./denial_management.db"
SYNC_DATABASE_URL = "sqlite:///./denial_management.db"

async_engine = create_async_engine(DATABASE_URL, echo=False)
sync_engine = create_engine(SYNC_DATABASE_URL, echo=False)

AsyncSessionLocal = sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False
)

Base = declarative_base()

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

async def init_db():
    """Initialize database tables and seed with data if empty"""
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Check if database is empty and seed if needed
    async with AsyncSessionLocal() as session:
        result = await session.execute(text("SELECT COUNT(*) FROM fact_claim"))
        count = result.scalar()
        
        if count == 0:
            print("Database is empty, seeding with synthetic data...")
            # Import and run seeding in a sync context
            from app.seed_data import seed_database
            seed_database()
            print("Database seeding complete!")
