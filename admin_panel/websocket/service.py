"""Service for handling widget messages."""
import logging
import secrets
import string
from typing import Optional
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from bot.database.models import TicketSource
from bot.database.crud import UserCRUD, TicketCRUD, MessageCRUD

logger = logging.getLogger(__name__)


def generate_topic_code() -> str:
    """Generate a random 8-character code for web topic names."""
    chars = string.ascii_uppercase + string.digits
    return ''.join(secrets.choice(chars) for _ in range(8))


class WidgetService:
    """Service for processing widget messages and managing web tickets."""

    def __init__(self, session: AsyncSession, bot=None):
        self.session = session
        self.bot = bot

    async def handle_visitor_message(
        self,
        visitor_id: str,
        text: str,
        page_url: Optional[str] = None,
        user_agent: Optional[str] = None,
        email: Optional[str] = None,
        first_name: Optional[str] = None,
    ) -> dict:
        """
        Handle a message from a visitor.

        Returns a dict with ticket_id, message_id, and status.
        """
        try:
            # Get or create user
            user, created = await UserCRUD.get_or_create_web_user(
                self.session,
                visitor_id=visitor_id,
                email=email,
                first_name=first_name,
            )

            if created:
                logger.info(f"Created new web user: visitor_id={visitor_id}")

            # Get or create ticket
            ticket = await TicketCRUD.get_open_by_user(self.session, user.id)
            is_new_ticket = ticket is None

            if is_new_ticket:
                # Generate topic name
                topic_code = generate_topic_code()
                topic_name = f"#WEB_{topic_code}"

                # Create ticket
                ticket = await TicketCRUD.create(
                    self.session,
                    user_id=user.id,
                    topic_name=topic_name,
                    source=TicketSource.WEB,
                    page_url=page_url,
                    user_agent=user_agent,
                )
                logger.info(f"Created new web ticket: {ticket.id} with topic name {topic_name}")

                # Create topic in Telegram if bot is available
                if self.bot:
                    await self._create_telegram_topic(ticket, user, page_url)

            # Save message to database
            message = await MessageCRUD.create(
                self.session,
                ticket_id=ticket.id,
                is_from_user=True,
                content_type="text",
                text=text,
                is_delivered=True,
            )

            # Send message to Telegram if bot is available
            if self.bot:
                await self._send_to_telegram(ticket, user, text, is_new_ticket, page_url)

            return {
                "status": "success",
                "ticket_id": ticket.id,
                "message_id": message.id,
                "is_new_ticket": is_new_ticket,
            }

        except Exception as e:
            logger.error(f"Error handling visitor message: {e}", exc_info=True)
            return {
                "status": "error",
                "error": str(e),
            }

    async def _create_telegram_topic(self, ticket, user, page_url: Optional[str]):
        """Create a topic in Telegram group for the web ticket."""
        try:
            from bot.config import settings

            topic_name = ticket.topic_name
            if len(topic_name) > 120:
                topic_name = topic_name[:120] + "..."

            forum_topic = await self.bot.create_forum_topic(
                chat_id=settings.support_group_id,
                name=topic_name,
            )
            topic_id = forum_topic.message_thread_id

            # Update ticket with topic ID
            await TicketCRUD.update_topic_id(self.session, ticket.id, topic_id)
            ticket.topic_id = topic_id

            logger.info(f"Created Telegram topic {topic_id} for ticket {ticket.id}")

        except Exception as e:
            logger.error(f"Failed to create Telegram topic for ticket {ticket.id}: {e}")

    async def _send_to_telegram(
        self,
        ticket,
        user,
        text: str,
        is_first: bool,
        page_url: Optional[str],
    ):
        """Send message to Telegram group."""
        try:
            from bot.config import settings

            if not ticket.topic_id:
                logger.warning(f"Ticket {ticket.id} has no topic_id, cannot send to Telegram")
                return

            # Create header
            header = self._create_message_header(ticket, user, is_first, page_url)

            # Send header
            await self.bot.send_message(
                chat_id=settings.support_group_id,
                message_thread_id=ticket.topic_id,
                text=header,
                parse_mode="HTML",
            )

            # Send actual message
            await self.bot.send_message(
                chat_id=settings.support_group_id,
                message_thread_id=ticket.topic_id,
                text=text,
            )

            logger.info(f"Sent message to Telegram for ticket {ticket.id}")

        except Exception as e:
            logger.error(f"Failed to send message to Telegram: {e}")

    def _create_message_header(
        self,
        ticket,
        user,
        is_first: bool,
        page_url: Optional[str],
    ) -> str:
        """Create header text for messages in Telegram group."""
        now = datetime.utcnow().strftime("%d.%m.%Y %H:%M")

        if is_first:
            header_parts = [
                f"<b>Новая заявка {ticket.ticket_id_str} (WEB)</b>",
                f"Тема: {ticket.topic_name}",
                f"Посетитель: {user.display_name}",
            ]

            if user.email:
                header_parts.append(f"Email: {user.email}")

            if page_url:
                header_parts.append(f"Страница: {page_url}")

            header_parts.extend([
                f"Дата: {now}",
                "─" * 30,
            ])
        else:
            header_parts = [
                f"<b>Сообщение от клиента</b> | {ticket.ticket_id_str}",
                "─" * 30,
            ]

        return "\n".join(header_parts)

    async def get_ticket_history(self, visitor_id: str) -> dict:
        """Get chat history for a visitor."""
        try:
            user = await UserCRUD.get_by_visitor_id(self.session, visitor_id)
            if not user:
                return {"status": "success", "messages": []}

            ticket = await TicketCRUD.get_open_by_user(self.session, user.id)
            if not ticket:
                return {"status": "success", "messages": []}

            messages = await MessageCRUD.get_by_ticket(self.session, ticket.id)

            return {
                "status": "success",
                "ticket_id": ticket.id,
                "messages": [
                    {
                        "id": msg.id,
                        "text": msg.text,
                        "is_from_user": msg.is_from_user,
                        "content_type": msg.content_type,
                        "created_at": msg.created_at.isoformat(),
                        "is_delivered": msg.is_delivered,
                        "is_read": msg.is_read,
                        "operator_username": msg.operator_username,
                    }
                    for msg in messages
                ],
            }

        except Exception as e:
            logger.error(f"Error getting ticket history: {e}", exc_info=True)
            return {"status": "error", "error": str(e)}

    async def mark_messages_as_read(self, visitor_id: str, message_ids: list[int]) -> dict:
        """Mark messages as read."""
        try:
            for message_id in message_ids:
                await MessageCRUD.mark_as_read(self.session, message_id)

            return {"status": "success"}

        except Exception as e:
            logger.error(f"Error marking messages as read: {e}", exc_info=True)
            return {"status": "error", "error": str(e)}
