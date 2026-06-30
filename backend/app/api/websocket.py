"""
WebSocket endpoint router.

Exposes `WS /ws/deployments` (§9).
Clients connect to receive real-time updates when deployments transition
between states (FAILED -> HEALING -> HEALED / FAILED_TO_HEAL).

Phase 1 is a one-way push channel. The server ignores any messages sent
by the client.
"""

import structlog
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.ws.manager import manager

logger = structlog.get_logger(__name__)

router = APIRouter(tags=["websocket"])


@router.websocket("/ws/deployments")
async def websocket_deployments(websocket: WebSocket) -> None:
    """
    WebSocket endpoint for real-time deployment status updates.

    Per §9:
    - Server accepts connection and registers client in the manager.
    - Does not send initial state proactively (client queries GET /api/deployments on mount).
    - Loops waiting for incoming messages (ignoring them if received) to keep connection alive.
    - Handles WebSocketDisconnect cleanly.
    """
    await manager.connect(websocket)
    try:
        while True:
            # We don't expect client messages in Phase 1, but we must await receive_text()
            # or receive() to keep the socket open and detect disconnects.
            await websocket.receive_text()
    except WebSocketDisconnect:
        logger.info("websocket.client_disconnected_normally")
    except Exception as exc:
        logger.error("websocket.error", error=str(exc))
    finally:
        manager.disconnect(websocket)
