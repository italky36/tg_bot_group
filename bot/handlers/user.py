import logging
from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import CommandStart, Command

from bot.database.session import async_session
from bot.database.crud import TicketCRUD
from bot.services.ticket import TicketService
from bot.utils.helpers import is_supported_content_type

logger = logging.getLogger(__name__)

router = Router(name="user")

# Filter: only private chats
router.message.filter(F.chat.type == "private")


@router.message(CommandStart())
async def cmd_start(message: Message):
    """Handle /start command in private chat."""
    welcome_text = (
        "<b>Добро пожаловать в службу поддержки!</b>\n\n"
        "Я помогу вам связаться с нашей командой поддержки.\n\n"
        "Просто напишите ваш вопрос или опишите проблему, "
        "и наши специалисты ответят вам в ближайшее время.\n\n"
        "Вы можете отправлять:\n"
        "• Текстовые сообщения\n"
        "• Фотографии и видео\n"
        "• Документы\n"
        "• Голосовые сообщения\n\n"
        "Используйте /help для получения справки."
    )
    await message.answer(welcome_text, parse_mode="HTML")


@router.message(Command("help"))
async def cmd_help(message: Message):
    """Handle /help command."""
    help_text = (
        "<b>Справка</b>\n\n"
        "<b>Как связаться с поддержкой:</b>\n"
        "Просто отправьте сообщение в этот чат. "
        "Наша команда получит его и ответит вам.\n\n"
        "<b>Поддерживаемые типы сообщений:</b>\n"
        "• Текст\n"
        "• Фото и видео\n"
        "• Документы (файлы)\n"
        "• Голосовые и видео-сообщения\n"
        "• Стикеры\n"
        "• Геолокация и контакты\n\n"
        "<b>Команды:</b>\n"
        "/start — начать работу с ботом\n"
        "/help — показать эту справку\n"
        "/my_tickets — мои заявки\n\n"
        "Среднее время ответа: 15-30 минут в рабочее время."
    )
    await message.answer(help_text, parse_mode="HTML")


@router.message(Command("my_tickets"))
async def cmd_my_tickets(message: Message):
    """Show user's tickets."""
    async with async_session() as session:
        service = TicketService(message.bot, session)
        user = await service.get_or_create_user(message.from_user)

        tickets = await TicketCRUD.get_all_by_user(session, user.id)

        if not tickets:
            await message.answer(
                "У вас пока нет обращений.\n"
                "Напишите нам, если у вас есть вопрос!"
            )
            return

        text = "<b>Ваши обращения:</b>\n\n"
        for ticket in tickets[:10]:  # Show last 10
            status_emoji = "" if ticket.status.value == "open" else ""
            created = ticket.created_at.strftime("%d.%m.%Y")
            text += f"{status_emoji} {ticket.ticket_id_str} — {created}\n"

        if len(tickets) > 10:
            text += f"\n<i>Показаны последние 10 из {len(tickets)} обращений</i>"

        await message.answer(text, parse_mode="HTML")


@router.message(F.content_type.in_({
    "text", "photo", "video", "document", "voice",
    "audio", "video_note", "sticker", "animation",
    "location", "contact"
}))
async def handle_user_message(message: Message):
    """Handle any message from user and forward to support group."""
    if not is_supported_content_type(message):
        await message.answer(
            "Извините, этот тип сообщения не поддерживается. "
            "Пожалуйста, отправьте текст, фото, видео или документ."
        )
        return

    async with async_session() as session:
        service = TicketService(message.bot, session)

        # Get or create user
        user = await service.get_or_create_user(message.from_user)

        # Get or create ticket
        ticket, is_new_ticket = await service.get_or_create_ticket(user)

        # Create topic if this is a new ticket
        if is_new_ticket:
            topic_id = await service.create_topic_for_ticket(ticket, user)
            if not topic_id:
                await message.answer(
                    "Произошла ошибка при создании обращения. "
                    "Пожалуйста, попробуйте позже или свяжитесь с нами другим способом."
                )
                return

        # Forward message to group
        success = await service.forward_user_message_to_group(
            message, ticket, user, is_first=is_new_ticket
        )

        if success:
            if is_new_ticket:
                await message.answer(
                    f"Ваше обращение принято под номером <b>{ticket.ticket_id_str}</b>.\n"
                    "Ожидайте ответа нашей поддержки.",
                    parse_mode="HTML"
                )
            # For subsequent messages, we don't send confirmation to avoid spam
        else:
            await message.answer(
                "Произошла ошибка при отправке сообщения. "
                "Пожалуйста, попробуйте ещё раз."
            )
