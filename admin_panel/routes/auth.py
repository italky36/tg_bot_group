from pathlib import Path

from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from starlette.status import HTTP_303_SEE_OTHER

from admin_panel.auth import verify_credentials, login_user, logout_user, is_authenticated

router = APIRouter(tags=["auth"])

BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=BASE_DIR / "templates")


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Show login page."""
    if is_authenticated(request):
        return RedirectResponse(url="/", status_code=HTTP_303_SEE_OTHER)

    return templates.TemplateResponse(
        "login.html",
        {"request": request, "error": None},
    )


@router.post("/login")
async def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
):
    """Process login form."""
    if verify_credentials(username, password):
        login_user(request)
        return RedirectResponse(url="/", status_code=HTTP_303_SEE_OTHER)

    return templates.TemplateResponse(
        "login.html",
        {"request": request, "error": "Неверный логин или пароль"},
        status_code=401,
    )


@router.get("/logout")
async def logout(request: Request):
    """Log out user."""
    logout_user(request)
    return RedirectResponse(url="/login", status_code=HTTP_303_SEE_OTHER)
