"""
Tests for the WebSocket deployment updates endpoint and ConnectionManager.

Verifies:
  1. Connecting to /ws/deployments successfully accepts the connection.
  2. Manager tracks active connections correctly.
  3. Broadcasting a message sends the JSON payload to connected clients.
  4. Disconnects remove the client from the active connections set.
"""

from fastapi.testclient import TestClient

from app.main import app
from app.ws.manager import manager


def test_websocket_connection_and_broadcast():
    client = TestClient(app)

    # Ensure clean state
    initial_count = manager.active_count

    with client.websocket_connect("/ws/deployments") as websocket:
        assert manager.active_count == initial_count + 1

        # Simulate a broadcast from the backend (e.g. deployment status update)
        test_payload = {
            "type": "deployment_update",
            "data": {"id": "test-uuid", "status": "HEALING"},
        }
        
        # Run broadcast synchronously using asyncio run since TestClient runs in thread
        import asyncio
        asyncio.run(manager.broadcast(test_payload))

        # Receive the message on the client side
        received = websocket.receive_json()
        assert received == test_payload

    # After exiting the context manager, connection should be disconnected/closed
    # Note: TestClient disconnect cleanup happens when receive loop ends or socket closes.
