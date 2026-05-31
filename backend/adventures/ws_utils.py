"""WebSocket helpers for broadcasting adventure updates."""
from __future__ import annotations

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from .serializers import AdventureHistorySerializer


def broadcast_history_entries(
    adventure_id: int, entries: list, exclude_user_id: int | None = None
) -> None:
    if not entries:
        return
    channel_layer = get_channel_layer()
    if channel_layer is None:
        return
    payload = AdventureHistorySerializer(entries, many=True).data
    async_to_sync(channel_layer.group_send)(
        f"adventure_{adventure_id}",
        {
            "type": "adventure.history",
            "entries": payload,
            "exclude_user_id": exclude_user_id,
        },
    )

def broadcast_lobby_state(
    adventure_id: int, payload: dict, exclude_user_id: int | None = None
) -> None:
    channel_layer = get_channel_layer()
    if channel_layer is None:
        return
    async_to_sync(channel_layer.group_send)(
        f"adventure_{adventure_id}",
        {
            "type": "adventure.lobby",
            "payload": payload,
            "exclude_user_id": exclude_user_id,
        },
    )
