"""Shared mixins for adventure views."""
from __future__ import annotations

from django.shortcuts import get_object_or_404
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import SAFE_METHODS

from ..utils import is_moderator

from ..models import Adventure, AdventurePlayer, ModerationEntry, PublishedAdventure


class AdventureTemplateMixin:
    def _has_run_access(self, adventure: Adventure) -> bool:
        if adventure.player_user_id == self.request.user.id:
            return True
        return AdventurePlayer.objects.filter(adventure=adventure, user=self.request.user).exists()

    def get_adventure(self) -> Adventure:
        if not hasattr(self, "_adventure"):
            if "template_id" in self.kwargs:
                adventure = get_object_or_404(
                    Adventure,
                    id=self.kwargs["template_id"],
                    is_template=True,
                )
                if adventure.author_user_id == self.request.user.id:
                    self._adventure = adventure
                elif (
                    self.request.method in SAFE_METHODS
                    and is_moderator(self.request.user)
                    and (
                        ModerationEntry.objects.filter(adventure=adventure).exists()
                        or PublishedAdventure.objects.filter(adventure=adventure).exists()
                    )
                ):
                    self._adventure = adventure
                else:
                    raise PermissionDenied("Недостаточно прав для доступа к приключению.")
            elif "run_id" in self.kwargs:
                adventure = get_object_or_404(
                    Adventure,
                    id=self.kwargs["run_id"],
                    is_template=False,
                )
                if adventure.player_user_id != self.request.user.id:
                    raise PermissionDenied("Недостаточно прав для доступа к приключению.")
                self._adventure = adventure
            else:
                raise ValueError("Adventure identifier is missing.")
        return self._adventure


class AdventureRunMixin:
    def _has_run_access(self, adventure: Adventure) -> bool:
        if adventure.player_user_id == self.request.user.id:
            return True
        return AdventurePlayer.objects.filter(adventure=adventure, user=self.request.user).exists()

    def get_adventure(self) -> Adventure:
        if not hasattr(self, "_adventure"):
            adventure = get_object_or_404(
                Adventure,
                id=self.kwargs["run_id"],
                is_template=False,
            )
            if not self._has_run_access(adventure):
                raise PermissionDenied("Недостаточно прав для доступа к приключению.")
            self._adventure = adventure
        return self._adventure

    def get_player_slot(self) -> AdventurePlayer | None:
        if not hasattr(self, "_player_slot"):
            adventure = self.get_adventure()
            self._player_slot = AdventurePlayer.objects.filter(
                adventure=adventure, user=self.request.user
            ).first()
            if (
                self._player_slot is None
                and adventure.player_user_id == self.request.user.id
            ):
                taken = set(
                    AdventurePlayer.objects.filter(adventure=adventure).values_list(
                        "slot_number", flat=True
                    )
                )
                for slot in range(1, adventure.max_players + 1):
                    if slot not in taken:
                        self._player_slot = AdventurePlayer.objects.create(
                            adventure=adventure,
                            user=self.request.user,
                            slot_number=slot,
                        )
                        break
        return self._player_slot
