from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base, Session
import os
import asyncio
from functools import partial
from urllib.parse import quote_plus

# Azure SQL Database Configuration - credentials from environment variables
AZURE_SQL_SERVER = os.getenv("AZURE_SQL_SERVER", "")
AZURE_SQL_DATABASE = os.getenv("AZURE_SQL_DATABASE", "")
AZURE_SQL_USER = os.getenv("AZURE_SQL_USER", "")
AZURE_SQL_PASSWORD = os.getenv("AZURE_SQL_PASSWORD", "")

# URL-encode the password to handle special characters like @
ENCODED_PASSWORD = quote_plus(AZURE_SQL_PASSWORD) if AZURE_SQL_PASSWORD else ""

# Use pymssql for SQL Server connections
if AZURE_SQL_SERVER and AZURE_SQL_DATABASE and AZURE_SQL_USER and AZURE_SQL_PASSWORD:
    SYNC_DATABASE_URL = f"mssql+pymssql://{AZURE_SQL_USER}:{ENCODED_PASSWORD}@{AZURE_SQL_SERVER}/{AZURE_SQL_DATABASE}"
else:
    # Fallback to SQLite for local development if Azure SQL credentials not provided
    SYNC_DATABASE_URL = "sqlite:///./denial_management.db"

# Create sync engine
sync_engine = create_engine(
    SYNC_DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    pool_size=5 if "mssql" in SYNC_DATABASE_URL else 1,
    max_overflow=10 if "mssql" in SYNC_DATABASE_URL else 0
)

# Create sync session factory
SyncSessionLocal = sessionmaker(
    bind=sync_engine,
    autocommit=False,
    autoflush=False
)

Base = declarative_base()

# Async wrapper for sync database operations
# This allows us to use the sync pymssql driver in an async context
class AsyncSessionWrapper:
    """Wrapper to make sync sessions work in async context"""
    def __init__(self, sync_session: Session):
        self._session = sync_session
        self._loop = None
    
    def _get_loop(self):
        if self._loop is None:
            try:
                self._loop = asyncio.get_running_loop()
            except RuntimeError:
                self._loop = asyncio.get_event_loop()
        return self._loop
    
    async def execute(self, statement, *args, **kwargs):
        """Execute a statement asynchronously"""
        func = partial(self._session.execute, statement, *args, **kwargs)
        return await self._get_loop().run_in_executor(None, func)
    
    async def commit(self):
        """Commit the transaction"""
        await self._get_loop().run_in_executor(None, self._session.commit)
    
    async def rollback(self):
        """Rollback the transaction"""
        await self._get_loop().run_in_executor(None, self._session.rollback)
    
    async def close(self):
        """Close the session"""
        await self._get_loop().run_in_executor(None, self._session.close)
    
    async def refresh(self, instance):
        """Refresh an instance"""
        func = partial(self._session.refresh, instance)
        await self._get_loop().run_in_executor(None, func)
    
    def add(self, instance):
        """Add an instance to the session"""
        self._session.add(instance)
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

class AsyncSessionFactory:
    """Factory for creating async session wrappers"""
    def __call__(self):
        return AsyncSessionWrapper(SyncSessionLocal())

AsyncSessionLocal = AsyncSessionFactory()

# Alias for background tasks
async_session_maker = AsyncSessionLocal

async def get_db():
    """Dependency for FastAPI routes to get database session"""
    session = AsyncSessionWrapper(SyncSessionLocal())
    try:
        yield session
    finally:
        await session.close()

async def init_db():
    """Initialize database - tables already exist in Azure SQL from migration"""
    db_type = "Azure SQL" if "mssql" in SYNC_DATABASE_URL else "SQLite"
    print(f"Connecting to {db_type} Database...")
    try:
        # Test connection
        with SyncSessionLocal() as session:
            result = session.execute(text("SELECT COUNT(*) FROM fact_claim"))
            count = result.scalar()
            print(f"Connected to {db_type}. Found {count} claims in database.")
    except Exception as e:
        print(f"Error connecting to {db_type}: {e}")
        raise
