import logging
import re
from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command

from bot.config import settings
from bot.database.session import async_session
from bot.database.crud import TicketCRUD
from bot.database.models import TicketStatus
from bot.services.ticket import TicketService
from bot.utils.helpers import is_supported_content_type, format_ticket_info

logger = logging.getLogger(__name__)

router = Router(name="group")

# Filter: only messages from the support group
router.message.filter(F.chat.id == settings.support_group_id)


@router.message(Command("close"))
async def cmd_close(message: Message):
    """Close a ticket. Usage: /close or /close [ticket_id]"""
    async with async_session() as session:
        service = TicketService(message.bot, session)

        # Try to get ticket ID from command arguments
        args = message.text.split()[1:] if message.text else []
        ticket_id = None

        if args:
            # Extract ticket ID from argument (e.g., "#0001" or "1")
            ticket_id_str = args[0].replace("#", "").strip()
            try:
                ticket_id = int(ticket_id_str)
            except ValueError:
                await message.answer(
                    "Неверный формат ID заявки. Используйте: /close #0001 или /close 1"
                )
                return
        elif message.message_thread_id:
            # Get ticket from current topic
            ticket = await TicketCRUD.get_by_topic_id(
                session, message.message_thread_id
            )
            if ticket:
                ticket_id = ticket.id

        if not ticket_id:
            await message.answer(
                "Не удалось определить заявку.\n"
                "Используйте команду в теме заявки или укажите ID: /close #0001"
            )
            return

        # Get operator info
        operator = message.from_user
        operator_name = f"@{operator.username}" if operator.username else operator.first_name

        # Close the ticket
        ticket = await service.close_ticket(ticket_id, operator_name)

        if ticket:
            await message.answer(
                f"Заявка {ticket.ticket_id_str} закрыта."
            )
        else:
            await message.answer("Заявка не найдена или уже закрыта.")


@router.message(Command("open"))
async def cmd_open(message: Message):
    """Reopen a closed ticket. Usage: /open or /open [ticket_id]"""
    async with async_session() as session:
        service = TicketService(message.bot, session)

        # Try to get ticket ID from command arguments
        args = message.text.split()[1:] if message.text else []
        ticket_id = None

        if args:
            ticket_id_str = args[0].replace("#", "").strip()
            try:
                ticket_id = int(ticket_id_str)
            except ValueError:
                await message.answer(
                    "Неверный формат ID заявки. Используйте: /open #0001 или /open 1"
                )
                return
        elif message.message_thread_id:
            ticket = await TicketCRUD.get_by_topic_id(
                session, message.message_thread_id
            )
            if ticket:
                ticket_id = ticket.id

        if not ticket_id:
            await message.answer(
                "Не удалось определить заявку.\n"
                "Используйте команду в теме заявки или укажите ID: /open #0001"
            )
            return

        ticket = await service.reopen_ticket(ticket_id)

        if ticket:
            await message.answer(
                f"Заявка {ticket.ticket_id_str} повторно открыта."
            )
        else:
            await message.answer("Заявка не найдена.")


@router.message(Command("info"))
async def cmd_info(message: Message):
    """Get information about a ticket. Usage: /info or /info [ticket_id]"""
    async with async_session() as session:
        # Try to get ticket ID from command arguments
        args = message.text.split()[1:] if message.text else []
        ticket_id = None

        if args:
            ticket_id_str = args[0].replace("#", "").strip()
            try:
                ticket_id = int(ticket_id_str)
            except ValueError:
                await message.answer(
                    "Неверный формат ID заявки. Используйте: /info #0001 или /info 1"
                )
                return
            ticket = await TicketCRUD.get_by_id(session, ticket_id)
        elif message.message_thread_id:
            ticket = await TicketCRUD.get_by_topic_id(
                session, message.message_thread_id
            )
        else:
            await message.answer(
                "Не удалось определить заявку.\n"
                "Используйте команду в теме заявки или укажите ID: /info #0001"
            )
            return

        if not ticket:
            await message.answer("Заявка не найдена.")
            return

        user = ticket.user
        info_text = format_ticket_info(ticket, user)
        await message.answer(info_text, parse_mode="HTML")


@router.message(Command("stats"))
async def cmd_stats(message: Message):
    """Show ticket statistics."""
    async with async_session() as session:
        stats = await TicketCRUD.get_statistics(session)

        stats_text = (
            "<b>Статистика заявок</b>\n\n"
            f"Всего заявок: {stats['total']}\n"
            f"Открытых: {stats['open']}\n"
            f"Закрытых: {stats['closed']}\n"
        )
        await message.answer(stats_text, parse_mode="HTML")


@router.message(F.message_thread_id, F.content_type.in_({
    "text", "photo", "video", "document", "voice",
    "audio", "video_note", "sticker", "animation",
    "location", "contact"
}))
async def handle_operator_message(message: Message):
    """Handle messages from operators in topic threads and forward to user."""
    # Skip if this is a command
    if message.text and message.text.startswith("/"):
        return

    # Skip bot's own messages
    if message.from_user.is_bot:
        return

    if not is_supported_content_type(message):
        return

    async with async_session() as session:
        # Find ticket by topic ID
        ticket = await TicketCRUD.get_by_topic_id(session, message.message_thread_id)

        if not ticket:
            logger.warning(
                f"No ticket found for topic {message.message_thread_id}"
            )
            return

        # Check if ticket is closed
        if ticket.status == TicketStatus.CLOSED:
            await message.reply(
                "Эта заявка закрыта. Используйте /open для повторного открытия."
            )
            return

        # Forward message to user
        service = TicketService(message.bot, session)
        operator_username = (
            f"@{message.from_user.username}"
            if message.from_user.username
            else message.from_user.first_name
        )

        success = await service.forward_operator_message_to_user(
            message, ticket, operator_username
        )

        if success:
            # React with checkmark to confirm delivery
            try:
                await message.react([{"type": "emoji", "emoji": ""}])
            except Exception:
                # Reaction might fail if bot doesn't have permission
                pass
        else:
            await message.reply(
                "Не удалось отправить сообщение пользователю."
            )
