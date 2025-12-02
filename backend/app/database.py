from sqlalchemy import create_engine, text, event
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
import sqlite3

DATABASE_URL = "sqlite+aiosqlite:///./denial_management.db"
SYNC_DATABASE_URL = "sqlite:///./denial_management.db"

# Enable WAL mode for better concurrency
def set_sqlite_pragma(dbapi_conn, connection_record):
    if isinstance(dbapi_conn, sqlite3.Connection):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=60000")  # 60 second timeout
        cursor.close()

# Configure SQLite for better concurrency with WAL mode and timeout
async_engine = create_async_engine(
    DATABASE_URL, 
    echo=False,
    connect_args={"timeout": 60, "check_same_thread": False},
    pool_pre_ping=True
)
sync_engine = create_engine(
    SYNC_DATABASE_URL, 
    echo=False,
    connect_args={"timeout": 60, "check_same_thread": False}
)

# Apply WAL mode to sync engine
event.listen(sync_engine, "connect", set_sqlite_pragma)

AsyncSessionLocal = sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Alias for background tasks
async_session_maker = AsyncSessionLocal

Base = declarative_base()

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

async def init_db():
    """Initialize database tables and seed with data if empty"""
    # Check if we need to recreate the schema (new columns added)
    needs_recreate = False
    try:
        async with AsyncSessionLocal() as session:
            # Check if new columns exist by querying them
            await session.execute(text("SELECT outcome FROM fact_appeal LIMIT 1"))
            await session.execute(text("SELECT needs_reeval FROM fact_denial LIMIT 1"))
    except Exception as e:
        print(f"Schema mismatch detected: {e}")
        needs_recreate = True
    
    if needs_recreate:
        print("Recreating database with updated schema...")
        async with async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
        # Reseed the database
        print("Reseeding database...")
        from app.seed_data import seed_database
        seed_database()
        print("Database recreation complete!")
        return
    
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
