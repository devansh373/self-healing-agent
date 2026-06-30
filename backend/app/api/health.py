"""
Health check router.

A simple endpoint that confirms the API is up and reachable.
No database call, no auth — just a heartbeat that load balancers,
monitoring tools, and humans can hit to verify the server is alive.
"""

from fastapi import APIRouter

# prefix="" because the route itself specifies the full path.
# tags=["health"] groups this endpoint in the auto-generated /docs UI.
router = APIRouter(tags=["health"])


@router.get("/api/health")
async def health_check() -> dict:
    """
    Returns 200 with {"status": "ok"} if the server is running.

    This endpoint is intentionally trivial — it doesn't check the database
    or any external dependency. Its only job is to confirm the ASGI process
    is alive and accepting HTTP requests. A more sophisticated readiness
    check (database ping, etc.) belongs in a separate /api/ready endpoint
    if needed later.
    """
    return {"status": "ok"}
