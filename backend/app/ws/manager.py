"""
WebSocket connection manager.

Maintains a set of active WebSocket connections and broadcasts
deployment updates to all connected clients simultaneously.

Phase 1 uses this as a one-way push channel — the server broadcasts
status transitions, clients never send messages.

Full implementation in Step 8. This module is created now so that
healing_service.py can import and call broadcast() without circular
dependency issues.
"""

import structlog
from fastapi import WebSocket

logger = structlog.get_logger(__name__)


class ConnectionManager:
    """
    Manages active WebSocket connections.

    Thread-safe for single-process asyncio usage (FastAPI runs in one
    event loop, so set operations aren't concurrent).
    """

    def __init__(self) -> None:
        self._connections: set[WebSocket] = set()

    async def connect(self, websocket: WebSocket) -> None:
        """Accept and register a new WebSocket connection."""
        await websocket.accept()
        self._connections.add(websocket)
        logger.info("websocket.connected", total_connections=len(self._connections))

    def disconnect(self, websocket: WebSocket) -> None:
        """Remove a WebSocket connection from the active set."""
        self._connections.discard(websocket)
        logger.info("websocket.disconnected", total_connections=len(self._connections))

    async def broadcast(self, message: dict) -> None:
        """
        Send a message to ALL connected clients.

        If a send fails (client disconnected between check and send),
        silently remove that connection — don't crash the broadcast loop.
        """
        dead_connections: list[WebSocket] = []

        for connection in self._connections:
            try:
                await connection.send_json(message)
            except Exception:
                dead_connections.append(connection)

        for dead in dead_connections:
            self._connections.discard(dead)
            logger.info("websocket.dead_connection_removed")

    @property
    def active_count(self) -> int:
        """Number of currently connected clients."""
        return len(self._connections)


# Module-level singleton — imported by healing_service and websocket router
manager = ConnectionManager()
