from aiogram.types import Message


def is_supported_content_type(message: Message) -> bool:
    """Check if the message contains a supported content type."""
    return any([
        message.text,
        message.photo,
        message.video,
        message.document,
        message.voice,
        message.audio,
        message.video_note,
        message.sticker,
        message.animation,
        message.location,
        message.contact,
    ])


def format_ticket_info(ticket, user) -> str:
    """Format ticket information for display."""
    status_emoji = "" if ticket.status.value == "open" else ""
    status_text = "Открыта" if ticket.status.value == "open" else "Закрыта"

    info = (
        f"<b>Информация о заявке {ticket.ticket_id_str}</b>\n\n"
        f"<b>Статус:</b> {status_emoji} {status_text}\n"
        f"<b>Пользователь:</b> {user.display_name}\n"
        f"<b>Telegram ID:</b> <code>{user.telegram_id}</code>\n"
        f"<b>Создана:</b> {ticket.created_at.strftime('%d.%m.%Y %H:%M')}\n"
    )

    if ticket.closed_at:
        info += f"<b>Закрыта:</b> {ticket.closed_at.strftime('%d.%m.%Y %H:%M')}\n"
        if ticket.closed_by:
            info += f"<b>Закрыл:</b> {ticket.closed_by}\n"

    return info
