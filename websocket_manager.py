"""
WebSocket connection manager for real-time notifications (Plan 4).
Manages per-user WebSocket connections for push notifications.
"""

import json
import logging
from typing import Dict, List

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections grouped by user_id."""

    def __init__(self):
        self._connections: Dict[int, List[WebSocket]] = {}

    async def connect(self, user_id: int, ws: WebSocket):
        await ws.accept()
        self._connections.setdefault(user_id, []).append(ws)
        logger.info("WebSocket connected: user_id=%s total=%s", user_id, len(self._connections.get(user_id, [])))

    def disconnect(self, user_id: int, ws: WebSocket):
        conns = self._connections.get(user_id, [])
        if ws in conns:
            conns.remove(ws)
        if not self._connections.get(user_id):
            self._connections.pop(user_id, None)
        logger.info("WebSocket disconnected: user_id=%s", user_id)

    async def send_notification(self, user_id: int, notification: dict):
        """Send a notification dict to all connections for a user."""
        conns = self._connections.get(user_id, [])
        message = json.dumps({"type": "notification", **notification})
        stale = []
        for ws in conns:
            try:
                await ws.send_text(message)
            except Exception:
                stale.append(ws)
        for ws in stale:
            self.disconnect(user_id, ws)

    async def broadcast_org(self, org_id: int, notification: dict, user_ids: List[int]):
        """Send notification to specific users in an org."""
        for uid in user_ids:
            await self.send_notification(uid, notification)


manager = ConnectionManager()
