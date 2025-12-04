from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Request, Query
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select, func

from admin_panel.auth import require_auth
from admin_panel.database import get_session, Ticket, User, Message, TicketStatus

router = APIRouter(prefix="/tickets", tags=["tickets"])

BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=BASE_DIR / "templates")


@router.get("", response_class=HTMLResponse)
@require_auth
async def tickets_list(
    request: Request,
    status: Optional[str] = Query(None, description="Filter by status"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
):
    """Show list of tickets with filtering."""
    async with get_session() as session:
        # Build query
        query = select(Ticket).order_by(Ticket.created_at.desc())
        count_query = select(func.count(Ticket.id))

        # Apply status filter
        if status == "open":
            query = query.where(Ticket.status == TicketStatus.OPEN)
            count_query = count_query.where(Ticket.status == TicketStatus.OPEN)
        elif status == "closed":
            query = query.where(Ticket.status == TicketStatus.CLOSED)
            count_query = count_query.where(Ticket.status == TicketStatus.CLOSED)

        # Get total count
        total_result = await session.execute(count_query)
        total = total_result.scalar() or 0

        # Apply pagination
        offset = (page - 1) * per_page
        query = query.offset(offset).limit(per_page)

        # Execute query
        result = await session.execute(query)
        tickets = result.scalars().all()

        # Calculate pagination info
        total_pages = (total + per_page - 1) // per_page

        return templates.TemplateResponse(
            "tickets.html",
            {
                "request": request,
                "tickets": tickets,
                "current_status": status,
                "page": page,
                "per_page": per_page,
                "total": total,
                "total_pages": total_pages,
            },
        )


@router.get("/{ticket_id}", response_class=HTMLResponse)
@require_auth
async def ticket_detail(request: Request, ticket_id: int):
    """Show ticket details with message history."""
    async with get_session() as session:
        # Get ticket
        ticket_result = await session.execute(
            select(Ticket).where(Ticket.id == ticket_id)
        )
        ticket = ticket_result.scalar_one_or_none()

        if not ticket:
            return templates.TemplateResponse(
                "error.html",
                {
                    "request": request,
                    "error": "Заявка не найдена",
                    "code": 404,
                },
                status_code=404,
            )

        # Get user
        user_result = await session.execute(
            select(User).where(User.id == ticket.user_id)
        )
        user = user_result.scalar_one_or_none()

        # Get messages
        messages_result = await session.execute(
            select(Message)
            .where(Message.ticket_id == ticket_id)
            .order_by(Message.created_at)
        )
        messages = messages_result.scalars().all()

        return templates.TemplateResponse(
            "ticket_detail.html",
            {
                "request": request,
                "ticket": ticket,
                "user": user,
                "messages": messages,
            },
        )
