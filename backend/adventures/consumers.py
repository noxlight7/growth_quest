"""WebSocket consumers for adventure updates."""
from __future__ import annotations

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer

from .models import Adventure, AdventurePlayer


@database_sync_to_async
def _has_access(user_id: int, run_id: int) -> bool:
    adventure = Adventure.objects.filter(id=run_id, is_template=False).first()
    if adventure is None:
        return False
    if adventure.player_user_id == user_id:
        return True
    return AdventurePlayer.objects.filter(adventure=adventure, user_id=user_id).exists()


class AdventureRunConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        user = self.scope.get("user")
        run_id = self.scope.get("url_route", {}).get("kwargs", {}).get("run_id")
        if not user or not user.is_authenticated or run_id is None:
            await self.close(code=4001)
            return
        if not await _has_access(user.id, int(run_id)):
            await self.close(code=4003)
            return
        self.run_id = int(run_id)
        self.group_name = f"adventure_{self.run_id}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, code):
        group = getattr(self, "group_name", None)
        if group:
            await self.channel_layer.group_discard(group, self.channel_name)

    async def adventure_history(self, event):
        exclude_user_id = event.get("exclude_user_id")
        if exclude_user_id and self.scope.get("user") and self.scope["user"].id == exclude_user_id:
            return
        await self.send_json({"type": "history", "entries": event.get("entries", [])})

    async def adventure_lobby(self, event):
        exclude_user_id = event.get("exclude_user_id")
        if exclude_user_id and self.scope.get("user") and self.scope["user"].id == exclude_user_id:
            return
        await self.send_json({"type": "lobby", "payload": event.get("payload", {})})
