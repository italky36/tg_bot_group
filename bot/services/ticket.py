import logging
from typing import Optional
from datetime import datetime

from aiogram import Bot
from aiogram.types import Message, User as TelegramUser
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import settings
from bot.database.crud import UserCRUD, TicketCRUD, MessageCRUD
from bot.database.models import Ticket, User, TicketStatus, TicketSource

logger = logging.getLogger(__name__)

# Global reference to connection manager (will be set during app initialization)
_connection_manager = None


def set_connection_manager(manager):
    """Set the global connection manager instance."""
    global _connection_manager
    _connection_manager = manager


def get_connection_manager():
    """Get the global connection manager instance."""
    return _connection_manager


class TicketService:
    """Service for managing support tickets."""

    def __init__(self, bot: Bot, session: AsyncSession):
        self.bot = bot
        self.session = session

    async def get_or_create_user(self, tg_user: TelegramUser) -> User:
        """Get or create a user from Telegram user data."""
        user, created = await UserCRUD.get_or_create(
            self.session,
            telegram_id=tg_user.id,
            username=tg_user.username,
            first_name=tg_user.first_name,
            last_name=tg_user.last_name,
        )
        if created:
            logger.info(f"Created new user: {user}")
        return user

    async def get_or_create_ticket(self, user: User) -> tuple[Ticket, bool]:
        """Get open ticket or create a new one. Returns (ticket, created)."""
        # Check for existing open ticket
        ticket = await TicketCRUD.get_open_by_user(self.session, user.id)
        if ticket:
            return ticket, False

        # Create new ticket
        ticket = await TicketCRUD.create(self.session, user.id)
        logger.info(f"Created new ticket: {ticket}")
        return ticket, True

    async def create_topic_for_ticket(
        self, ticket: Ticket, user: User
    ) -> Optional[int]:
        """Create a topic in the support group for the ticket."""
        try:
            topic_name = user.display_name
            # Truncate if too long (Telegram limit is 128 chars)
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

            logger.info(f"Created topic {topic_id} for ticket {ticket.id}")
            return topic_id
        except Exception as e:
            logger.error(
                f"Failed to create topic for ticket {ticket.id}: {e}. "
                f"Check that: 1) Group {settings.support_group_id} exists, "
                f"2) Bot is admin with 'Manage Topics' permission, "
                f"3) Group has Topics enabled"
            )
            return None

    async def forward_user_message_to_group(
        self, message: Message, ticket: Ticket, user: User, is_first: bool = False
    ) -> bool:
        """Forward a user's message to the support group topic."""
        try:
            if not ticket.topic_id:
                logger.error(f"Ticket {ticket.id} has no topic_id")
                return False

            # Create header for the message
            header = self._create_user_message_header(ticket, user, is_first)

            # Send header message
            await self.bot.send_message(
                chat_id=settings.support_group_id,
                message_thread_id=ticket.topic_id,
                text=header,
                parse_mode="HTML",
            )

            # Forward the actual message content
            await self._forward_content_to_group(message, ticket)

            # Record message in database
            content_type = self._get_content_type(message)
            await MessageCRUD.create(
                self.session,
                ticket_id=ticket.id,
                telegram_message_id=message.message_id,
                is_from_user=True,
                content_type=content_type,
                text=message.text or message.caption,
            )

            return True
        except Exception as e:
            logger.error(f"Failed to forward message to group: {e}")
            return False

    async def forward_operator_message_to_user(
        self, message: Message, ticket: Ticket, operator_username: Optional[str] = None
    ) -> bool:
        """Forward an operator's message to the user (Telegram)."""
        try:
            # Get user from ticket
            user = ticket.user

            # Forward the message content to user
            await self._forward_content_to_user(message, user.telegram_id)

            # Record message in database
            content_type = self._get_content_type(message)
            await MessageCRUD.create(
                self.session,
                ticket_id=ticket.id,
                telegram_message_id=message.message_id,
                is_from_user=False,
                content_type=content_type,
                text=message.text or message.caption,
                operator_username=operator_username,
            )

            return True
        except Exception as e:
            logger.error(f"Failed to forward message to user: {e}")
            return False

    async def forward_operator_message_to_web_user(
        self, message: Message, ticket: Ticket, operator_username: Optional[str] = None
    ) -> bool:
        """Forward an operator's message to web user via WebSocket."""
        try:
            # Get user from ticket
            user = ticket.user

            if not user.visitor_id:
                logger.error(f"Web ticket {ticket.id} has no visitor_id")
                return False

            # Only support text messages for now
            if not message.text:
                logger.warning(f"Non-text message to web user not yet supported")
                return False

            # Send via WebSocket
            connection_manager = get_connection_manager()
            if not connection_manager:
                logger.error("Connection manager not initialized")
                return False

            ws_message = {
                "type": "message",
                "text": message.text,
                "is_from_user": False,
                "operator_username": operator_username,
                "created_at": datetime.utcnow().isoformat(),
            }

            success = await connection_manager.send_personal_message(
                ws_message,
                user.visitor_id
            )

            if not success:
                logger.warning(f"Failed to send message via WebSocket to {user.visitor_id}")
                # User might be offline - message is still saved in DB
            else:
                logger.info(f"Sent message to web visitor {user.visitor_id}")

            # Record message in database
            await MessageCRUD.create(
                self.session,
                ticket_id=ticket.id,
                telegram_message_id=message.message_id,
                is_from_user=False,
                content_type="text",
                text=message.text,
                operator_username=operator_username,
                is_delivered=success,
            )

            return True

        except Exception as e:
            logger.error(f"Failed to forward message to web user: {e}")
            return False

    async def close_ticket(
        self, ticket_id: int, closed_by: Optional[str] = None
    ) -> Optional[Ticket]:
        """Close a ticket and notify the user."""
        ticket = await TicketCRUD.close(self.session, ticket_id, closed_by)
        if not ticket:
            return None

        user = ticket.user

        # Notify user based on ticket source
        try:
            if ticket.source == TicketSource.WEB:
                # Notify web user via WebSocket
                if user.visitor_id:
                    connection_manager = get_connection_manager()
                    if connection_manager:
                        await connection_manager.send_personal_message(
                            {"type": "closed"},
                            user.visitor_id
                        )
                        logger.info(f"Sent close notification to web visitor {user.visitor_id}")
            else:
                # Notify Telegram user
                close_message = (
                    f"Диалог по заявке {ticket.ticket_id_str} завершён.\n\n"
                    "Если у вас появится новый вопрос, просто напишите нам новое сообщение."
                )
                await self.bot.send_message(
                    chat_id=user.telegram_id,
                    text=close_message,
                )
        except Exception as e:
            logger.error(f"Failed to notify user about ticket closure: {e}")

        # Send confirmation to group
        try:
            closed_by_text = f" ({closed_by})" if closed_by else ""
            group_message = f"Заявка {ticket.ticket_id_str} закрыта{closed_by_text}"
            await self.bot.send_message(
                chat_id=settings.support_group_id,
                message_thread_id=ticket.topic_id,
                text=group_message,
            )
        except Exception as e:
            logger.error(f"Failed to send close confirmation to group: {e}")

        return ticket

    async def reopen_ticket(self, ticket_id: int) -> Optional[Ticket]:
        """Reopen a closed ticket."""
        ticket = await TicketCRUD.reopen(self.session, ticket_id)
        if not ticket:
            return None

        # Notify user
        try:
            user = ticket.user
            reopen_message = (
                f"Заявка {ticket.ticket_id_str} была повторно открыта.\n"
                "Вы можете продолжить общение с поддержкой."
            )
            await self.bot.send_message(
                chat_id=user.telegram_id,
                text=reopen_message,
            )
        except Exception as e:
            logger.error(f"Failed to notify user about ticket reopening: {e}")

        return ticket

    def _create_user_message_header(
        self, ticket: Ticket, user: User, is_first: bool
    ) -> str:
        """Create header text for user messages in the group."""
        now = datetime.utcnow().strftime("%d.%m.%Y %H:%M")

        if is_first:
            header = (
                f"<b>Новая заявка {ticket.ticket_id_str}</b>\n"
                f"Пользователь: {user.display_name}\n"
                f"ID: <code>{user.telegram_id}</code>\n"
                f"Дата: {now}\n"
                f"{'─' * 20}"
            )
        else:
            header = (
                f"<b>Сообщение от клиента</b> | {ticket.ticket_id_str}\n"
                f"{'─' * 20}"
            )
        return header

    async def _forward_content_to_group(
        self, message: Message, ticket: Ticket
    ) -> None:
        """Forward message content to the group topic."""
        chat_id = settings.support_group_id
        thread_id = ticket.topic_id

        # Handle different content types
        if message.text:
            await self.bot.send_message(
                chat_id=chat_id,
                message_thread_id=thread_id,
                text=message.text,
            )
        elif message.photo:
            await self.bot.send_photo(
                chat_id=chat_id,
                message_thread_id=thread_id,
                photo=message.photo[-1].file_id,
                caption=message.caption,
            )
        elif message.video:
            await self.bot.send_video(
                chat_id=chat_id,
                message_thread_id=thread_id,
                video=message.video.file_id,
                caption=message.caption,
            )
        elif message.document:
            await self.bot.send_document(
                chat_id=chat_id,
                message_thread_id=thread_id,
                document=message.document.file_id,
                caption=message.caption,
            )
        elif message.voice:
            await self.bot.send_voice(
                chat_id=chat_id,
                message_thread_id=thread_id,
                voice=message.voice.file_id,
            )
        elif message.audio:
            await self.bot.send_audio(
                chat_id=chat_id,
                message_thread_id=thread_id,
                audio=message.audio.file_id,
                caption=message.caption,
            )
        elif message.video_note:
            await self.bot.send_video_note(
                chat_id=chat_id,
                message_thread_id=thread_id,
                video_note=message.video_note.file_id,
            )
        elif message.sticker:
            await self.bot.send_sticker(
                chat_id=chat_id,
                message_thread_id=thread_id,
                sticker=message.sticker.file_id,
            )
        elif message.animation:
            await self.bot.send_animation(
                chat_id=chat_id,
                message_thread_id=thread_id,
                animation=message.animation.file_id,
                caption=message.caption,
            )
        elif message.location:
            await self.bot.send_location(
                chat_id=chat_id,
                message_thread_id=thread_id,
                latitude=message.location.latitude,
                longitude=message.location.longitude,
            )
        elif message.contact:
            await self.bot.send_contact(
                chat_id=chat_id,
                message_thread_id=thread_id,
                phone_number=message.contact.phone_number,
                first_name=message.contact.first_name,
                last_name=message.contact.last_name,
            )

    async def _forward_content_to_user(
        self, message: Message, user_telegram_id: int
    ) -> None:
        """Forward message content to the user."""
        # Prepend "Поддержка:" label for text messages
        prefix = "<b>Поддержка:</b>\n"

        if message.text:
            await self.bot.send_message(
                chat_id=user_telegram_id,
                text=f"{prefix}{message.text}",
                parse_mode="HTML",
            )
        elif message.photo:
            caption = f"{prefix}{message.caption}" if message.caption else prefix.strip()
            await self.bot.send_photo(
                chat_id=user_telegram_id,
                photo=message.photo[-1].file_id,
                caption=caption,
                parse_mode="HTML",
            )
        elif message.video:
            caption = f"{prefix}{message.caption}" if message.caption else prefix.strip()
            await self.bot.send_video(
                chat_id=user_telegram_id,
                video=message.video.file_id,
                caption=caption,
                parse_mode="HTML",
            )
        elif message.document:
            caption = f"{prefix}{message.caption}" if message.caption else prefix.strip()
            await self.bot.send_document(
                chat_id=user_telegram_id,
                document=message.document.file_id,
                caption=caption,
                parse_mode="HTML",
            )
        elif message.voice:
            await self.bot.send_message(
                chat_id=user_telegram_id,
                text=prefix.strip(),
                parse_mode="HTML",
            )
            await self.bot.send_voice(
                chat_id=user_telegram_id,
                voice=message.voice.file_id,
            )
        elif message.audio:
            caption = f"{prefix}{message.caption}" if message.caption else prefix.strip()
            await self.bot.send_audio(
                chat_id=user_telegram_id,
                audio=message.audio.file_id,
                caption=caption,
                parse_mode="HTML",
            )
        elif message.video_note:
            await self.bot.send_message(
                chat_id=user_telegram_id,
                text=prefix.strip(),
                parse_mode="HTML",
            )
            await self.bot.send_video_note(
                chat_id=user_telegram_id,
                video_note=message.video_note.file_id,
            )
        elif message.sticker:
            await self.bot.send_message(
                chat_id=user_telegram_id,
                text=prefix.strip(),
                parse_mode="HTML",
            )
            await self.bot.send_sticker(
                chat_id=user_telegram_id,
                sticker=message.sticker.file_id,
            )
        elif message.animation:
            caption = f"{prefix}{message.caption}" if message.caption else prefix.strip()
            await self.bot.send_animation(
                chat_id=user_telegram_id,
                animation=message.animation.file_id,
                caption=caption,
                parse_mode="HTML",
            )
        elif message.location:
            await self.bot.send_message(
                chat_id=user_telegram_id,
                text=prefix.strip(),
                parse_mode="HTML",
            )
            await self.bot.send_location(
                chat_id=user_telegram_id,
                latitude=message.location.latitude,
                longitude=message.location.longitude,
            )
        elif message.contact:
            await self.bot.send_message(
                chat_id=user_telegram_id,
                text=prefix.strip(),
                parse_mode="HTML",
            )
            await self.bot.send_contact(
                chat_id=user_telegram_id,
                phone_number=message.contact.phone_number,
                first_name=message.contact.first_name,
                last_name=message.contact.last_name,
            )

    @staticmethod
    def _get_content_type(message: Message) -> str:
        """Determine the content type of a message."""
        if message.text:
            return "text"
        elif message.photo:
            return "photo"
        elif message.video:
            return "video"
        elif message.document:
            return "document"
        elif message.voice:
            return "voice"
        elif message.audio:
            return "audio"
        elif message.video_note:
            return "video_note"
        elif message.sticker:
            return "sticker"
        elif message.animation:
            return "animation"
        elif message.location:
            return "location"
        elif message.contact:
            return "contact"
        return "unknown"
