from functools import wraps
from typing import Callable

from fastapi import Request, HTTPException
from fastapi.responses import RedirectResponse
from starlette.status import HTTP_303_SEE_OTHER

from admin_panel.config import admin_settings


def verify_credentials(username: str, password: str) -> bool:
    """Verify admin credentials."""
    return (
        username == admin_settings.admin_username
        and password == admin_settings.admin_password
    )


def login_user(request: Request) -> None:
    """Set user as logged in."""
    request.session["authenticated"] = True


def logout_user(request: Request) -> None:
    """Log out user."""
    request.session.clear()


def is_authenticated(request: Request) -> bool:
    """Check if user is authenticated."""
    return request.session.get("authenticated", False)


def require_auth(func: Callable) -> Callable:
    """Decorator to require authentication for route handlers."""
    @wraps(func)
    async def wrapper(request: Request, *args, **kwargs):
        if not is_authenticated(request):
            return RedirectResponse(
                url="/login",
                status_code=HTTP_303_SEE_OTHER,
            )
        return await func(request, *args, **kwargs)
    return wrapper
