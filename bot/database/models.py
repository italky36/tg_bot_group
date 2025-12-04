from datetime import datetime
from enum import Enum
from typing import Optional, List

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    String,
    Text,
    Enum as SQLEnum,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all database models."""
    pass


class TicketStatus(str, Enum):
    """Ticket status enumeration."""
    OPEN = "open"
    CLOSED = "closed"


class User(Base):
    """User model - represents Telegram users who contact support."""
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    first_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    last_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    tickets: Mapped[List["Ticket"]] = relationship(
        "Ticket", back_populates="user", lazy="selectin"
    )

    @property
    def display_name(self) -> str:
        """Get user display name."""
        if self.username:
            return f"@{self.username}"
        if self.first_name:
            name = self.first_name
            if self.last_name:
                name += f" {self.last_name}"
            return name
        return f"User {self.telegram_id}"

    def __repr__(self) -> str:
        return f"<User(id={self.id}, telegram_id={self.telegram_id}, username={self.username})>"


class Ticket(Base):
    """Ticket model - represents a support request/conversation thread."""
    __tablename__ = "tickets"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    topic_id: Mapped[int] = mapped_column(BigInteger, nullable=True, index=True)
    status: Mapped[TicketStatus] = mapped_column(
        SQLEnum(TicketStatus), default=TicketStatus.OPEN
    )
    closed_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="tickets")
    messages: Mapped[List["Message"]] = relationship(
        "Message", back_populates="ticket", lazy="selectin"
    )

    @property
    def ticket_id_str(self) -> str:
        """Get formatted ticket ID."""
        return f"#{self.id:04d}"

    def __repr__(self) -> str:
        return f"<Ticket(id={self.id}, user_id={self.user_id}, status={self.status})>"


class Message(Base):
    """Message model - stores message history for tickets."""
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    ticket_id: Mapped[int] = mapped_column(ForeignKey("tickets.id"), index=True)
    telegram_message_id: Mapped[int] = mapped_column(BigInteger)
    is_from_user: Mapped[bool] = mapped_column(default=True)
    content_type: Mapped[str] = mapped_column(String(50), default="text")
    text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    operator_username: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )

    # Relationships
    ticket: Mapped["Ticket"] = relationship("Ticket", back_populates="messages")

    def __repr__(self) -> str:
        return f"<Message(id={self.id}, ticket_id={self.ticket_id}, is_from_user={self.is_from_user})>"
