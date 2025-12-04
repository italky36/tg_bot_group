from aiogram import Router

from bot.handlers.user import router as user_router
from bot.handlers.group import router as group_router


def setup_routers() -> Router:
    """Setup and combine all routers."""
    main_router = Router()
    main_router.include_router(user_router)
    main_router.include_router(group_router)
    return main_router


__all__ = ["setup_routers"]
