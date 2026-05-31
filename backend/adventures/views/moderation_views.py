"""Views for adventure moderation workflow."""
from __future__ import annotations

from rest_framework import generics, permissions, status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from ..models import Adventure, ModerationEntry, PublishedAdventure
from ..serializers import ModerationEntrySerializer, PublishedAdventureSerializer
from ..utils import is_moderator


class ModerationQueueListView(generics.ListAPIView):
    serializer_class = ModerationEntrySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if not is_moderator(self.request.user):
            raise PermissionDenied("Недостаточно прав для модерации.")
        return (
            ModerationEntry.objects.select_related("adventure", "adventure__author_user")
            .order_by("-submitted_at")
        )


class PublishedAdventureListView(generics.ListAPIView):
    serializer_class = PublishedAdventureSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return (
            PublishedAdventure.objects.select_related("adventure", "adventure__author_user")
            .order_by("-published_at")
        )


class AdventureSubmitForModerationView(generics.CreateAPIView):
    serializer_class = ModerationEntrySerializer
    permission_classes = [permissions.IsAuthenticated]

    def create(self, request, *args, **kwargs):  # type: ignore[override]
        adventure = Adventure.objects.filter(
            id=self.kwargs["template_id"],
            is_template=True,
            author_user=request.user,
        ).first()
        if not adventure:
            raise PermissionDenied("Нельзя отправить это приключение на модерацию.")
        if PublishedAdventure.objects.filter(adventure=adventure).exists():
            raise ValidationError("Приключение уже опубликовано.")
        if ModerationEntry.objects.filter(adventure=adventure).exists():
            raise ValidationError("Приключение уже на модерации.")
        entry = ModerationEntry.objects.create(adventure=adventure)
        serializer = self.get_serializer(entry)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class ModerationDecisionView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def _get_entry(self):
        if not is_moderator(self.request.user):
            raise PermissionDenied("Недостаточно прав для модерации.")
        return ModerationEntry.objects.select_related("adventure").filter(
            adventure_id=self.kwargs["template_id"]
        ).first()

    def post(self, request, *args, **kwargs):  # type: ignore[override]
        entry = self._get_entry()
        if not entry:
            raise ValidationError("Приключение не найдено в очереди модерации.")
        decision = self.kwargs.get("decision")
        if decision == "publish":
            if PublishedAdventure.objects.filter(adventure=entry.adventure).exists():
                raise ValidationError("Приключение уже опубликовано.")
            PublishedAdventure.objects.create(adventure=entry.adventure)
        elif decision != "reject":
            raise ValidationError("Неизвестное действие модерации.")
        entry.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
