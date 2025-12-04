from datetime import datetime
from typing import Optional, List

from sqlalchemy import select, update
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models import User, Ticket, Message, TicketStatus


class UserCRUD:
    """CRUD operations for User model."""

    @staticmethod
    async def get_by_telegram_id(
        session: AsyncSession, telegram_id: int
    ) -> Optional[User]:
        """Get user by Telegram ID."""
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def create(
        session: AsyncSession,
        telegram_id: int,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
    ) -> User:
        """Create a new user."""
        user = User(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user

    @staticmethod
    async def get_or_create(
        session: AsyncSession,
        telegram_id: int,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
    ) -> tuple[User, bool]:
        """Get existing user or create a new one. Returns (user, created)."""
        user = await UserCRUD.get_by_telegram_id(session, telegram_id)
        if user:
            # Update user info if changed
            if (user.username != username or
                user.first_name != first_name or
                user.last_name != last_name):
                user.username = username
                user.first_name = first_name
                user.last_name = last_name
                await session.commit()
            return user, False
        user = await UserCRUD.create(
            session, telegram_id, username, first_name, last_name
        )
        return user, True


class TicketCRUD:
    """CRUD operations for Ticket model."""

    @staticmethod
    async def get_by_id(session: AsyncSession, ticket_id: int) -> Optional[Ticket]:
        """Get ticket by ID."""
        result = await session.execute(
            select(Ticket)
            .options(selectinload(Ticket.user))
            .where(Ticket.id == ticket_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_topic_id(
        session: AsyncSession, topic_id: int
    ) -> Optional[Ticket]:
        """Get ticket by topic ID."""
        result = await session.execute(
            select(Ticket)
            .options(selectinload(Ticket.user))
            .where(Ticket.topic_id == topic_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_open_by_user(
        session: AsyncSession, user_id: int
    ) -> Optional[Ticket]:
        """Get open ticket for a user."""
        result = await session.execute(
            select(Ticket).where(
                Ticket.user_id == user_id,
                Ticket.status == TicketStatus.OPEN
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_all_by_user(
        session: AsyncSession, user_id: int
    ) -> List[Ticket]:
        """Get all tickets for a user."""
        result = await session.execute(
            select(Ticket).where(Ticket.user_id == user_id).order_by(Ticket.created_at.desc())
        )
        return list(result.scalars().all())

    @staticmethod
    async def create(
        session: AsyncSession,
        user_id: int,
        topic_id: Optional[int] = None,
    ) -> Ticket:
        """Create a new ticket."""
        ticket = Ticket(
            user_id=user_id,
            topic_id=topic_id,
            status=TicketStatus.OPEN,
        )
        session.add(ticket)
        await session.commit()
        await session.refresh(ticket)
        return ticket

    @staticmethod
    async def update_topic_id(
        session: AsyncSession, ticket_id: int, topic_id: int
    ) -> None:
        """Update ticket's topic ID."""
        await session.execute(
            update(Ticket).where(Ticket.id == ticket_id).values(topic_id=topic_id)
        )
        await session.commit()

    @staticmethod
    async def close(
        session: AsyncSession, ticket_id: int, closed_by: Optional[str] = None
    ) -> Optional[Ticket]:
        """Close a ticket."""
        ticket = await TicketCRUD.get_by_id(session, ticket_id)
        if ticket:
            ticket.status = TicketStatus.CLOSED
            ticket.closed_by = closed_by
            ticket.closed_at = datetime.utcnow()
            await session.commit()
            await session.refresh(ticket)
        return ticket

    @staticmethod
    async def reopen(session: AsyncSession, ticket_id: int) -> Optional[Ticket]:
        """Reopen a closed ticket."""
        ticket = await TicketCRUD.get_by_id(session, ticket_id)
        if ticket:
            ticket.status = TicketStatus.OPEN
            ticket.closed_by = None
            ticket.closed_at = None
            await session.commit()
            await session.refresh(ticket)
        return ticket

    @staticmethod
    async def get_statistics(session: AsyncSession) -> dict:
        """Get ticket statistics."""
        from sqlalchemy import func

        # Total tickets
        total_result = await session.execute(select(func.count(Ticket.id)))
        total = total_result.scalar() or 0

        # Open tickets
        open_result = await session.execute(
            select(func.count(Ticket.id)).where(Ticket.status == TicketStatus.OPEN)
        )
        open_count = open_result.scalar() or 0

        # Closed tickets
        closed_count = total - open_count

        return {
            "total": total,
            "open": open_count,
            "closed": closed_count,
        }


class MessageCRUD:
    """CRUD operations for Message model."""

    @staticmethod
    async def create(
        session: AsyncSession,
        ticket_id: int,
        telegram_message_id: int,
        is_from_user: bool = True,
        content_type: str = "text",
        text: Optional[str] = None,
        operator_username: Optional[str] = None,
    ) -> Message:
        """Create a new message record."""
        message = Message(
            ticket_id=ticket_id,
            telegram_message_id=telegram_message_id,
            is_from_user=is_from_user,
            content_type=content_type,
            text=text,
            operator_username=operator_username,
        )
        session.add(message)
        await session.commit()
        await session.refresh(message)
        return message

    @staticmethod
    async def get_by_ticket(
        session: AsyncSession, ticket_id: int
    ) -> List[Message]:
        """Get all messages for a ticket."""
        result = await session.execute(
            select(Message)
            .where(Message.ticket_id == ticket_id)
            .order_by(Message.created_at)
        )
        return list(result.scalars().all())
