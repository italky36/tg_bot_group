import logging
from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from contextlib import asynccontextmanager

from admin_panel.config import admin_settings

# Import models from bot package
import sys
from pathlib import Path

# Add parent directory to path to import bot models
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bot.database.models import Base, User, Ticket, Message, TicketStatus
logger = logging.getLogger(__name__)

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

# Simple SQLite-safe migrations to align existing databases with current models.
MIGRATIONS = {
    "users": {
        "visitor_id": "ALTER TABLE users ADD COLUMN visitor_id VARCHAR(255)",
        "email": "ALTER TABLE users ADD COLUMN email VARCHAR(255)",
    },
    "tickets": {
        "topic_name": "ALTER TABLE tickets ADD COLUMN topic_name VARCHAR(255)",
        "source": "ALTER TABLE tickets ADD COLUMN source VARCHAR(20) DEFAULT 'telegram'",
        "page_url": "ALTER TABLE tickets ADD COLUMN page_url TEXT",
        "user_agent": "ALTER TABLE tickets ADD COLUMN user_agent TEXT",
    },
    "messages": {
        "is_delivered": "ALTER TABLE messages ADD COLUMN is_delivered BOOLEAN NOT NULL DEFAULT 0",
        "is_read": "ALTER TABLE messages ADD COLUMN is_read BOOLEAN NOT NULL DEFAULT 0",
    },
}


async def ensure_schema():
    """
    Add missing columns to existing SQLite databases.

    Older installations created the DB before new fields (topic_name, source, etc.)
    were added to the models, which causes runtime SELECT errors. We inspect the
    current schema and apply lightweight ALTER TABLE statements only when needed.
    """
    async with engine.begin() as conn:
        def apply_migrations(connection):
            inspector = inspect(connection)
            for table, columns in MIGRATIONS.items():
                existing = {col["name"] for col in inspector.get_columns(table)}
                for column, ddl in columns.items():
                    if column not in existing:
                        logger.info(f"Adding missing column {table}.{column}")
                        connection.exec_driver_sql(ddl)

            # Make telegram_id nullable to support web visitors without Telegram accounts
            users_cols = {col["name"]: col for col in inspector.get_columns("users")}
            telegram_col = users_cols.get("telegram_id")
            if telegram_col and not telegram_col.get("nullable", True):
                logger.info("Rebuilding users table to allow NULL telegram_id")
                connection.exec_driver_sql("PRAGMA foreign_keys=OFF;")
                connection.exec_driver_sql(
                    """
                    CREATE TABLE IF NOT EXISTS users_new (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        telegram_id BIGINT UNIQUE,
                        visitor_id VARCHAR(255) UNIQUE,
                        username VARCHAR(255),
                        first_name VARCHAR(255),
                        last_name VARCHAR(255),
                        email VARCHAR(255),
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL
                    );
                    """
                )
                connection.exec_driver_sql(
                    """
                    INSERT INTO users_new (id, telegram_id, visitor_id, username, first_name, last_name, email, created_at, updated_at)
                    SELECT id, telegram_id, visitor_id, username, first_name, last_name, email, created_at, updated_at FROM users;
                    """
                )
                connection.exec_driver_sql("DROP TABLE users;")
                connection.exec_driver_sql("ALTER TABLE users_new RENAME TO users;")
                connection.exec_driver_sql("PRAGMA foreign_keys=ON;")

            # Make telegram_message_id nullable to support non-TG messages
            messages_cols = {col["name"]: col for col in inspector.get_columns("messages")}
            tmsg_col = messages_cols.get("telegram_message_id")
            if tmsg_col and not tmsg_col.get("nullable", True):
                logger.info("Rebuilding messages table to allow NULL telegram_message_id")
                connection.exec_driver_sql("PRAGMA foreign_keys=OFF;")
                connection.exec_driver_sql(
                    """
                    CREATE TABLE IF NOT EXISTS messages_new (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        ticket_id INTEGER NOT NULL,
                        telegram_message_id BIGINT,
                        is_from_user BOOLEAN NOT NULL DEFAULT 1,
                        content_type VARCHAR(50) NOT NULL DEFAULT 'text',
                        text TEXT,
                        operator_username VARCHAR(255),
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
                        is_delivered BOOLEAN NOT NULL DEFAULT 0,
                        is_read BOOLEAN NOT NULL DEFAULT 0,
                        FOREIGN KEY(ticket_id) REFERENCES tickets(id)
                    );
                    """
                )
                connection.exec_driver_sql(
                    """
                    INSERT INTO messages_new (id, ticket_id, telegram_message_id, is_from_user, content_type, text, operator_username, created_at, is_delivered, is_read)
                    SELECT id, ticket_id, telegram_message_id, is_from_user, content_type, text, operator_username, created_at, is_delivered, is_read FROM messages;
                    """
                )
                connection.exec_driver_sql("DROP TABLE messages;")
                connection.exec_driver_sql("ALTER TABLE messages_new RENAME TO messages;")
                connection.exec_driver_sql("PRAGMA foreign_keys=ON;")

            # Normalize enum values that may be uppercase or invalid from old data
            connection.exec_driver_sql(
                "UPDATE tickets SET status = LOWER(status) "
                "WHERE status NOT IN ('open','closed') OR status != LOWER(status)"
            )
            connection.exec_driver_sql(
                "UPDATE tickets SET source = LOWER(source) "
                "WHERE source NOT IN ('telegram','web') OR source != LOWER(source)"
            )

        await conn.run_sync(apply_migrations)


async def get_db():
    """
    Async generator that yields a database session.

    This form is convenient for FastAPI dependencies or manual
    iteration with `async for` (see WebSocket routes).
    """
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()


@asynccontextmanager
async def get_session():
    """Get database session as async context manager."""
    async for session in get_db():
        yield session


__all__ = [
    "ensure_schema",
    "get_db",
    "get_session",
    "User",
    "Ticket",
    "Message",
    "TicketStatus",
]
