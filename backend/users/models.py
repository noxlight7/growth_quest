"""
Custom user model for the game application.

This model extends Django's AbstractUser to add a ``credits`` field
representing the number of in-game credits a user possesses.
"""
from __future__ import annotations

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Custom user model with additional credits field."""

    email = models.EmailField(unique=True)
    credits = models.PositiveIntegerField(default=0, help_text="Number of credits available to the user.")
    def __str__(self) -> str:
        return self.username


class Administrator(models.Model):
    """Application-level administrators with hierarchical levels."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="administrator_profile",
    )
    level = models.PositiveSmallIntegerField()

    def __str__(self) -> str:
        return f"{self.user.username} (level {self.level})"
