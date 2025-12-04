from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from contextlib import asynccontextmanager

from admin_panel.config import admin_settings

# Import models from bot package
import sys
from pathlib import Path

# Add parent directory to path to import bot models
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bot.database.models import Base, User, Ticket, Message, TicketStatus

# Create engine for admin panel
engine = create_async_engine(
    admin_settings.database_url,
    echo=False,
    future=True,
)

async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@asynccontextmanager
async def get_session():
    """Get database session as async context manager."""
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()


__all__ = [
    "get_session",
    "User",
    "Ticket",
    "Message",
    "TicketStatus",
]
