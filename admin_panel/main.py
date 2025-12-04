from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from admin_panel.config import admin_settings
from admin_panel.database import ensure_schema
from admin_panel.routes import dashboard, tickets, auth, widget

# Get base directory
BASE_DIR = Path(__file__).resolve().parent

# Create FastAPI app
app = FastAPI(
    title="SupportHub Admin",
    description="Admin panel for Telegram Support Bot",
    version="1.0.0",
)

# Add session middleware
app.add_middleware(
    SessionMiddleware,
    secret_key=admin_settings.admin_secret_key,
)

# Mount static files
app.mount(
    "/static",
    StaticFiles(directory=BASE_DIR / "static"),
    name="static",
)

# Mount widget files
import os
widget_dir = BASE_DIR.parent / "widget"
if os.path.exists(widget_dir):
    app.mount(
        "/widget",
        StaticFiles(directory=widget_dir),
        name="widget",
    )

# Setup templates
templates = Jinja2Templates(directory=BASE_DIR / "templates")

# Ensure database schema is up to date on startup
@app.on_event("startup")
async def startup_event():
    await ensure_schema()

# Include routers
app.include_router(auth.router)
app.include_router(dashboard.router)
app.include_router(tickets.router)
app.include_router(widget.router)
