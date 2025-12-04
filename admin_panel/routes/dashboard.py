from pathlib import Path
from datetime import datetime, timedelta

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select, func

from admin_panel.auth import require_auth
from admin_panel.database import get_session, Ticket, Message, TicketStatus

router = APIRouter(tags=["dashboard"])

BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=BASE_DIR / "templates")


@router.get("/", response_class=HTMLResponse)
@require_auth
async def dashboard(request: Request):
    """Show dashboard with statistics."""
    async with get_session() as session:
        # Total tickets
        total_result = await session.execute(select(func.count(Ticket.id)))
        total_tickets = total_result.scalar() or 0

        # Open tickets
        open_result = await session.execute(
            select(func.count(Ticket.id)).where(Ticket.status == TicketStatus.OPEN)
        )
        open_tickets = open_result.scalar() or 0

        # Closed tickets
        closed_tickets = total_tickets - open_tickets

        # Today's tickets
        today = datetime.utcnow().date()
        today_start = datetime.combine(today, datetime.min.time())
        today_result = await session.execute(
            select(func.count(Ticket.id)).where(Ticket.created_at >= today_start)
        )
        today_tickets = today_result.scalar() or 0

        # This week's tickets
        week_ago = datetime.utcnow() - timedelta(days=7)
        week_result = await session.execute(
            select(func.count(Ticket.id)).where(Ticket.created_at >= week_ago)
        )
        week_tickets = week_result.scalar() or 0

        # Recent tickets (last 5)
        recent_result = await session.execute(
            select(Ticket)
            .order_by(Ticket.created_at.desc())
            .limit(5)
        )
        recent_tickets = recent_result.scalars().all()

        # Calculate average response time (for closed tickets)
        avg_response_time = None
        closed_with_messages = await session.execute(
            select(Ticket)
            .where(Ticket.status == TicketStatus.CLOSED)
            .where(Ticket.closed_at.isnot(None))
            .limit(100)
        )
        closed_list = closed_with_messages.scalars().all()

        if closed_list:
            response_times = []
            for ticket in closed_list:
                # Get first operator message
                first_response = await session.execute(
                    select(Message)
                    .where(Message.ticket_id == ticket.id)
                    .where(Message.is_from_user == False)
                    .order_by(Message.created_at)
                    .limit(1)
                )
                first_msg = first_response.scalar_one_or_none()
                if first_msg:
                    diff = first_msg.created_at - ticket.created_at
                    response_times.append(diff.total_seconds())

            if response_times:
                avg_seconds = sum(response_times) / len(response_times)
                avg_minutes = int(avg_seconds / 60)
                if avg_minutes < 60:
                    avg_response_time = f"{avg_minutes} мин"
                else:
                    avg_response_time = f"{avg_minutes // 60} ч {avg_minutes % 60} мин"

        stats = {
            "total": total_tickets,
            "open": open_tickets,
            "closed": closed_tickets,
            "today": today_tickets,
            "week": week_tickets,
            "avg_response_time": avg_response_time or "—",
        }

        return templates.TemplateResponse(
            "dashboard.html",
            {
                "request": request,
                "stats": stats,
                "recent_tickets": recent_tickets,
            },
        )
