import logging
from collections import defaultdict
import anyio
from fastapi import WebSocket
from sqlalchemy.orm import Session
from app.domain.models import GroupMember

logger = logging.getLogger(__name__)


class GroupHub:
    """In-memory registry of WebSocket connections per group (single-process only)."""

    def __init__(self) -> None:
        self._connections: dict[str, set[WebSocket]] = defaultdict(set)

    def add(self, group_id: str, ws: WebSocket) -> None:
        self._connections[group_id].add(ws)

    def remove(self, group_id: str, ws: WebSocket) -> None:
        self._connections[group_id].discard(ws)
        if not self._connections[group_id]:
            del self._connections[group_id]

    async def broadcast(self, group_ids: list[str], message: dict) -> None:
        for group_id in group_ids:
            for ws in list(self._connections.get(group_id, ())):
                try:
                    await ws.send_json({**message, "group_id": group_id})
                except Exception:
                    self.remove(group_id, ws)


hub = GroupHub()


def notify_groups(group_ids: list[str], event: str = "leaderboard_changed") -> None:
    """Called from sync (threadpool) endpoints after the DB commit. Never raises."""
    if not group_ids:
        return
    try:
        anyio.from_thread.run(hub.broadcast, [str(g) for g in group_ids], {"type": event})
    except Exception:
        logger.exception("Failed to broadcast group update")


def notify_user_groups(db: Session, user_id) -> None:
    group_ids = [g for (g,) in db.query(GroupMember.group_id).filter(GroupMember.user_id == user_id)]
    notify_groups(group_ids)
