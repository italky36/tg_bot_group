from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Request, Query, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from admin_panel.auth import require_auth
from admin_panel.config import admin_settings
from admin_panel.database import get_session, Ticket, User, Message, TicketStatus
from admin_panel.websocket.manager import connection_manager
from bot.database.crud import MessageCRUD, TicketCRUD

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
        query = (
            select(Ticket)
            .options(selectinload(Ticket.user))
            .order_by(Ticket.created_at.desc())
        )
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
            select(Ticket)
            .options(selectinload(Ticket.user))
            .where(Ticket.id == ticket_id)
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
        messages = await MessageCRUD.get_by_ticket(session, ticket_id)

        return templates.TemplateResponse(
            "ticket_detail.html",
            {
                "request": request,
                "ticket": ticket,
                "user": user,
                "messages": messages,
            },
        )


@router.get("/{ticket_id}/messages")
@require_auth
async def ticket_messages(request: Request, ticket_id: int):
    """Return messages for a ticket as JSON (for live updates)."""
    async with get_session() as session:
        ticket = await TicketCRUD.get_by_id(session, ticket_id)
        if not ticket:
            raise HTTPException(status_code=404, detail="Ticket not found")

        # Mark all user messages as read when operator fetches them
        await MessageCRUD.mark_ticket_messages_read(session, ticket_id)

        messages = await MessageCRUD.get_by_ticket(session, ticket_id)

        # Push read receipt to visitor if connected
        visitor_id = ticket.user.visitor_id if ticket.user else None
        if visitor_id:
            await connection_manager.send_personal_message(
                {"type": "read_receipt"},
                visitor_id,
            )

        return {
            "messages": [
                {
                    "id": msg.id,
                    "text": msg.text,
                    "is_from_user": msg.is_from_user,
                    "content_type": msg.content_type,
                    "created_at": msg.created_at.isoformat(),
                    "operator_username": msg.operator_username,
                    "is_delivered": msg.is_delivered,
                    "is_read": msg.is_read,
                }
                for msg in messages
            ]
        }


@router.post("/{ticket_id}/reply")
@require_auth
async def ticket_reply(request: Request, ticket_id: int):
    """Send a reply to a ticket (stores in DB and pushes to visitor if connected)."""
    payload = await request.json()
    text = (payload.get("text") or "").strip()

    if not text:
        return JSONResponse({"status": "error", "error": "Empty message"}, status_code=400)

    async with get_session() as session:
        ticket = await TicketCRUD.get_by_id(session, ticket_id)
        if not ticket:
            raise HTTPException(status_code=404, detail="Ticket not found")

        message = await MessageCRUD.create(
            session,
            ticket_id=ticket.id,
            is_from_user=False,
            content_type="text",
            text=text,
            operator_username=admin_settings.admin_username,
            is_delivered=True,
            is_read=False,
        )

        # Push to visitor via WebSocket if connected
        visitor_id = ticket.user.visitor_id if ticket.user else None
        if visitor_id:
            await connection_manager.send_personal_message(
                {
                    "type": "message",
                    "text": message.text,
                    "is_from_user": False,
                    "created_at": message.created_at.isoformat(),
                    "is_delivered": True,
                    "is_read": False,
                    "operator_username": message.operator_username,
                },
                visitor_id,
            )

        return {"status": "success", "message_id": message.id}
