"""WebSocket connection manager for chat widget."""
import logging
from typing import Dict, Set
from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections for the chat widget."""

    def __init__(self):
        # visitor_id -> WebSocket connection
        self.active_connections: Dict[str, WebSocket] = {}
        # topic_id -> Set of operator websockets (for future operator dashboard)
        self.operator_connections: Dict[int, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, visitor_id: str):
        """Accept a new WebSocket connection."""
        await websocket.accept()
        self.active_connections[visitor_id] = websocket
        logger.info(f"WebSocket connected for visitor {visitor_id}")

    def disconnect(self, visitor_id: str):
        """Remove a WebSocket connection."""
        if visitor_id in self.active_connections:
            del self.active_connections[visitor_id]
            logger.info(f"WebSocket disconnected for visitor {visitor_id}")

    async def send_personal_message(self, message: dict, visitor_id: str):
        """Send a message to a specific visitor."""
        websocket = self.active_connections.get(visitor_id)
        if websocket:
            try:
                await websocket.send_json(message)
                logger.debug(f"Sent message to visitor {visitor_id}: {message}")
                return True
            except Exception as e:
                logger.error(f"Error sending message to visitor {visitor_id}: {e}")
                self.disconnect(visitor_id)
                return False
        return False

    def get_connection(self, visitor_id: str) -> WebSocket | None:
        """Get WebSocket connection for a visitor."""
        return self.active_connections.get(visitor_id)

    def is_connected(self, visitor_id: str) -> bool:
        """Check if visitor is connected."""
        return visitor_id in self.active_connections


# Global connection manager instance
connection_manager = ConnectionManager()
