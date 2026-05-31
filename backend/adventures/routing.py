"""WebSocket routing for adventures."""
from __future__ import annotations

from django.urls import path

from .consumers import AdventureRunConsumer

websocket_urlpatterns = [
    path("ws/adventures/<int:run_id>/", AdventureRunConsumer.as_asgi()),
]
