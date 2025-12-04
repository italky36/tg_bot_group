"""WebSocket routes for chat widget."""
import logging
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from admin_panel.database import get_db
from admin_panel.websocket.manager import connection_manager
from admin_panel.websocket.service import WidgetService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/ws/widget/{visitor_id}")
async def websocket_endpoint(websocket: WebSocket, visitor_id: str):
    """
    WebSocket endpoint for chat widget.

    The visitor_id should be generated on the client side and stored in localStorage.
    """
    await connection_manager.connect(websocket, visitor_id)

    # Get database session
    async for session in get_db():
        service = WidgetService(session)

        try:
            # Send initial connection confirmation
            await websocket.send_json({
                "type": "connected",
                "visitor_id": visitor_id,
            })

            # Load chat history if exists
            history = await service.get_ticket_history(visitor_id)
            if history.get("status") == "success" and history.get("messages"):
                await websocket.send_json({
                    "type": "history",
                    "messages": history["messages"],
                })

            # Listen for messages
            while True:
                try:
                    data = await websocket.receive_text()
                    message = json.loads(data)

                    message_type = message.get("type")

                    if message_type == "message":
                        # Handle incoming message from visitor
                        result = await service.handle_visitor_message(
                            visitor_id=visitor_id,
                            text=message.get("text", ""),
                            page_url=message.get("page_url"),
                            user_agent=message.get("user_agent"),
                            email=message.get("email"),
                            first_name=message.get("first_name"),
                        )

                        # Send confirmation back to visitor
                        await websocket.send_json({
                            "type": "message_sent",
                            "message_id": result.get("message_id"),
                            "ticket_id": result.get("ticket_id"),
                            "status": result.get("status"),
                        })

                    elif message_type == "mark_read":
                        # Mark messages as read
                        message_ids = message.get("message_ids", [])
                        await service.mark_messages_as_read(visitor_id, message_ids)

                    elif message_type == "ping":
                        # Keep-alive ping
                        await websocket.send_json({"type": "pong"})

                except json.JSONDecodeError:
                    logger.error(f"Invalid JSON received from {visitor_id}")
                    await websocket.send_json({
                        "type": "error",
                        "error": "Invalid JSON format",
                    })

        except WebSocketDisconnect:
            logger.info(f"WebSocket disconnected for visitor {visitor_id}")
        except Exception as e:
            logger.error(f"Error in WebSocket connection for {visitor_id}: {e}", exc_info=True)
        finally:
            connection_manager.disconnect(visitor_id)
            break
