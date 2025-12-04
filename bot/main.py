import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from bot.config import settings
from bot.database.session import init_db
from bot.handlers import setup_routers


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)


async def on_startup(bot: Bot) -> None:
    """Actions to perform on bot startup."""
    logger.info("Initializing database...")
    await init_db()

    # Verify bot can access the support group
    try:
        chat = await bot.get_chat(settings.support_group_id)
        if not chat.is_forum:
            logger.warning(
                f"Support group {chat.title} does not have topics enabled! "
                "Please enable topics in group settings."
            )
        else:
            logger.info(f"Connected to support group: {chat.title}")
    except Exception as e:
        logger.error(f"Cannot access support group: {e}")
        logger.error(
            "Make sure the bot is added to the group and has admin rights "
            "with 'Manage Topics' permission."
        )

    bot_info = await bot.get_me()
    logger.info(f"Bot started: @{bot_info.username}")


async def on_shutdown(bot: Bot) -> None:
    """Actions to perform on bot shutdown."""
    logger.info("Bot is shutting down...")


async def main() -> None:
    """Main function to start the bot."""
    # Initialize bot
    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    # Initialize dispatcher
    dp = Dispatcher()

    # Setup routers
    main_router = setup_routers()
    dp.include_router(main_router)

    # Register startup and shutdown handlers
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    # Start polling
    logger.info("Starting bot...")
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
