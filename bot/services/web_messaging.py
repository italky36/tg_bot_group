"""Service for sending messages to web widget via WebSocket."""
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class WebMessagingService:
    """Service for sending messages to web widget users."""

    def __init__(self, connection_manager):
        """
        Initialize WebMessagingService.

        Args:
            connection_manager: Instance of ConnectionManager from admin_panel.websocket.manager
        """
        self.connection_manager = connection_manager

    async def send_operator_message(
        self,
        visitor_id: str,
        text: str,
        operator_username: Optional[str] = None,
    ) -> bool:
        """
        Send a message from operator to web visitor.

        Args:
            visitor_id: Unique visitor ID
            text: Message text
            operator_username: Username of the operator

        Returns:
            True if message was sent, False otherwise
        """
        try:
            message = {
                "type": "message",
                "text": text,
                "is_from_user": False,
                "operator_username": operator_username,
                "created_at": None,  # Will be set by frontend
            }

            success = await self.connection_manager.send_personal_message(message, visitor_id)
            if success:
                logger.info(f"Sent operator message to visitor {visitor_id}")
            else:
                logger.warning(f"Visitor {visitor_id} is not connected")

            return success

        except Exception as e:
            logger.error(f"Error sending operator message to {visitor_id}: {e}")
            return False

    async def send_chat_closed(self, visitor_id: str) -> bool:
        """
        Notify web visitor that chat has been closed.

        Args:
            visitor_id: Unique visitor ID

        Returns:
            True if notification was sent, False otherwise
        """
        try:
            message = {
                "type": "closed",
            }

            success = await self.connection_manager.send_personal_message(message, visitor_id)
            if success:
                logger.info(f"Sent chat closed notification to visitor {visitor_id}")

            return success

        except Exception as e:
            logger.error(f"Error sending chat closed notification to {visitor_id}: {e}")
            return False

    def is_visitor_online(self, visitor_id: str) -> bool:
        """
        Check if visitor is currently connected.

        Args:
            visitor_id: Unique visitor ID

        Returns:
            True if visitor is online, False otherwise
        """
        return self.connection_manager.is_connected(visitor_id)
