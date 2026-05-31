from __future__ import annotations

from users.models import Administrator


def get_admin_level(user) -> int | None:
    if not user or not user.is_authenticated:
        return None
    try:
        return user.administrator_profile.level
    except Administrator.DoesNotExist:
        return None


def is_moderator(user) -> bool:
    return get_admin_level(user) is not None
