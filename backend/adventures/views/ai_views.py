"""Views that invoke AI generation for adventure history."""
from __future__ import annotations

import logging

from django.db import transaction
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from backend.llm import get_llm_client

from .base import AdventureRunMixin
from .history_utils import _extract_json_payload, _prepare_history_for_prompt, _set_ai_waiting
from .prompts import (
    _build_generation_prompt,
    _build_npc_generation_prompt,
    _split_party_characters,
    _story_text,
    _story_text_for_locale,
)
from ..models import Adventure, AdventureHistory, AdventurePlayer
from ..serializers import AdventureHistorySerializer
from ..services.localization import get_string, get_user_locale
from ..services.orchestrator import after_ai_turn, after_user_turn, before_user_turn
from ..services.turn_analysis import revert_analysis_for_history_entries
from ..ws_utils import broadcast_history_entries

logger = logging.getLogger(__name__)


def _generate_ai_entry(
    adventure: Adventure,
    include_npcs: bool = False,
    exclude_user_id: int | None = None,
):
    with transaction.atomic():
        locked = Adventure.objects.select_for_update().get(id=adventure.id)
        if locked.is_waiting_ai:
            return (
                None,
                None,
                {"detail": "Model response is already in progress."},
                status.HTTP_409_CONFLICT,
            )
        locked.is_waiting_ai = True
        locked.save(update_fields=["is_waiting_ai"])
    try:
        client = get_llm_client()
        history_entries = _prepare_history_for_prompt(adventure, client)
        base_max_tokens = 500
        max_tokens = base_max_tokens
        npc_names = []
        word_limit = "160-200"
        if adventure.story_reduced_text_length:
            word_limit = "70-100"
            max_tokens = min(max_tokens, 320)
        prompt = _build_generation_prompt(adventure, history_entries, word_limit=word_limit)
        if include_npcs:
            _, npc_characters = _split_party_characters(adventure)
            npc_names = [character.title for character in npc_characters]
            if npc_names:
                prompt = _build_npc_generation_prompt(
                    adventure,
                    history_entries,
                    npc_names,
                    word_limit=word_limit,
                )
                max_tokens = min(1400, base_max_tokens + len(npc_names) * 120)
                if adventure.story_reduced_text_length:
                    max_tokens = min(max_tokens, 360)
        if adventure.story_simple_language:
            prompt += f" {_story_text(adventure, 'simple_language')}"
        response = client.generate(prompt=prompt, max_tokens=max_tokens)
        raw_text = response.text.strip()
        metadata = {}
        if include_npcs:
            metadata["include_npcs"] = True
        story_text = raw_text
        npc_actions = []
        if include_npcs and npc_names:
            payload = _extract_json_payload(raw_text)
            if payload and isinstance(payload.get("story"), str):
                story_text = payload.get("story", "").strip()
            raw_actions = payload.get("npc_actions", []) if payload else []
            allowed_npc_names = {name.strip().lower() for name in npc_names if name}
            single_npc_name = npc_names[0].strip() if len(npc_names) == 1 else ""
            if isinstance(raw_actions, list):
                for entry in raw_actions:
                    if isinstance(entry, dict):
                        name = str(entry.get("name", "")).strip()
                        action = str(entry.get("action", "")).strip()
                        if not name and action and single_npc_name:
                            name = single_npc_name
                        if name and allowed_npc_names and name.lower() not in allowed_npc_names:
                            continue
                        if name or action:
                            label = name or _story_text(adventure, "npc")
                            npc_actions.append(f"{label}: {action}".strip(": "))
                    elif isinstance(entry, str) and entry.strip():
                        cleaned_entry = entry.strip()
                        if allowed_npc_names:
                            matched = any(
                                cleaned_entry.lower().startswith(f"{allowed.lower()}:")
                                for allowed in npc_names
                            )
                            if not matched:
                                continue
                        npc_actions.append(cleaned_entry)
            elif isinstance(raw_actions, str) and raw_actions.strip():
                npc_actions.append(raw_actions.strip())
        if not story_text:
            raise ValueError("Empty model response.")
        npc_entry = None
        with transaction.atomic():
            if npc_actions:
                npc_entry = AdventureHistory.objects.create(
                    adventure=adventure,
                    role=AdventureHistory.Role.AI,
                    content=_story_text(adventure, "npc_moves")
                    + "\n"
                    + "\n".join(f"• {line}" for line in npc_actions),
                    metadata={
                        "npc_entry": True,
                        "npc_actions": npc_actions,
                        "include_npcs": True,
                    },
                )
                metadata["npc_entry_id"] = npc_entry.id
            entry = AdventureHistory.objects.create(
                adventure=adventure,
                role=AdventureHistory.Role.AI,
                content=story_text,
                metadata=metadata,
            )
        broadcast_history_entries(
            adventure.id,
            [e for e in (npc_entry, entry) if e],
            exclude_user_id=exclude_user_id,
        )
        after_ai_turn(adventure, entry)
    except ValueError as exc:
        _set_ai_waiting(adventure.id, False)
        logger.warning("AI generation failed.", exc_info=exc)
        return None, None, {"detail": "Model response failed."}, status.HTTP_502_BAD_GATEWAY
    except Exception:
        _set_ai_waiting(adventure.id, False)
        logger.exception("AI generation failed.")
        return None, None, {"detail": "Model response failed."}, status.HTTP_502_BAD_GATEWAY
    _set_ai_waiting(adventure.id, False)
    AdventurePlayer.objects.filter(adventure=adventure, is_npc=False).update(wrote_after_ai=False)
    AdventurePlayer.objects.filter(adventure=adventure, is_npc=True).update(wrote_after_ai=True)
    return entry, npc_entry, None, None


def _create_user_history_entry(
    adventure: Adventure,
    content: str,
    exclude_user_id: int | None = None,
    metadata: dict | None = None,
) -> AdventureHistory:
    entry = AdventureHistory.objects.create(
        adventure=adventure,
        role=AdventureHistory.Role.USER,
        content=content,
        metadata=metadata or {},
    )
    broadcast_history_entries(adventure.id, [entry], exclude_user_id=exclude_user_id)
    return entry


def format_player_move_content(
    content: str,
    *,
    hero_name: str = "",
    hero_state: str = "",
    story_locale: str = Adventure.StoryLocale.RU,
) -> str:
    parts = []
    if hero_name:
        parts.append(f"{hero_name}: {content}")
    else:
        parts.append(content)
    if hero_state:
        parts.append(_story_text_for_locale(story_locale, "explicit_hero_state", state=hero_state))
    return "\n".join(parts)


def _finalize_user_turn(
    adventure: Adventure,
    player_slot: AdventurePlayer,
    include_npcs: bool,
    exclude_user_id: int | None = None,
):
    player_slot.wrote_after_ai = True
    player_slot.save(update_fields=["wrote_after_ai"])
    if AdventurePlayer.objects.filter(
        adventure=adventure, wrote_after_ai=False, is_npc=False
    ).exists():
        return None, None, None, True
    ai_entry, npc_entry, error_data, _ = _generate_ai_entry(
        adventure,
        include_npcs=include_npcs,
        exclude_user_id=exclude_user_id,
    )
    return ai_entry, npc_entry, error_data, False


class AdventureRunHistoryGenerateView(AdventureRunMixin, APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, run_id):
        adventure = self.get_adventure()
        if adventure.started_at is None:
            return Response({"detail": "Adventure not started."}, status=status.HTTP_400_BAD_REQUEST)
        entry, _, error_data, error_status = _generate_ai_entry(
            adventure,
            exclude_user_id=request.user.id,
        )
        if error_data:
            return Response(error_data, status=error_status)
        return Response(AdventureHistorySerializer(entry).data, status=status.HTTP_201_CREATED)


class AdventureRunHeroPromptView(AdventureRunMixin, APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, run_id):
        adventure = self.get_adventure()
        if adventure.started_at is None:
            return Response({"detail": "Adventure not started."}, status=status.HTTP_400_BAD_REQUEST)
        if adventure.is_waiting_ai:
            return Response(
                {"detail": "Model response is already in progress."},
                status=status.HTTP_409_CONFLICT,
            )
        player_slot = self.get_player_slot()
        if player_slot is None or player_slot.hero_id is None:
            return Response({"detail": "Hero not selected."}, status=status.HTTP_400_BAD_REQUEST)
        payload = request.data or {}
        content = (payload.get("content") or "").strip()
        hero_state = (payload.get("hero_state") or "").strip()
        if not content:
            return Response({"detail": "Content is required."}, status=status.HTTP_400_BAD_REQUEST)
        hero_name = player_slot.hero.title if player_slot.hero else ""
        entry_content = format_player_move_content(
            content,
            hero_name=hero_name,
            hero_state=hero_state,
            story_locale=adventure.story_locale,
        )
        safety = before_user_turn(adventure, request.user, entry_content)
        if safety.action == "block":
            return Response(
                {
                    "detail": get_string(get_user_locale(request.user), "blocked"),
                    "safety": {
                        "risk_level": safety.risk_level,
                        "categories": safety.categories,
                        "action": safety.action,
                    },
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        user_entry = _create_user_history_entry(
            adventure,
            entry_content,
            exclude_user_id=request.user.id,
            metadata={"hero_state": hero_state} if hero_state else {},
        )
        after_user_turn(adventure, request.user, user_entry)
        ai_entry, npc_entry, error_data, pending = _finalize_user_turn(
            adventure,
            player_slot,
            include_npcs=True,
            exclude_user_id=request.user.id,
        )
        if pending:
            return Response(
                {"user_entry": AdventureHistorySerializer(user_entry).data, "ai_entry": None},
                status=status.HTTP_201_CREATED,
            )
        if error_data:
            return Response(
                {
                    "detail": error_data.get("detail"),
                    "user_entry": AdventureHistorySerializer(user_entry).data,
                    "npc_entry": None,
                    "ai_entry": None,
                },
                status=status.HTTP_201_CREATED,
            )
        return Response(
            {
                "user_entry": AdventureHistorySerializer(user_entry).data,
                "npc_entry": AdventureHistorySerializer(npc_entry).data if npc_entry else None,
                "ai_entry": AdventureHistorySerializer(ai_entry).data if ai_entry else None,
            },
            status=status.HTTP_201_CREATED,
        )


class AdventureRunHistoryRollbackView(AdventureRunMixin, APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, run_id, entry_id):
        adventure = self.get_adventure()
        if adventure.started_at is None:
            return Response({"detail": "Adventure not started."}, status=status.HTTP_400_BAD_REQUEST)
        with transaction.atomic():
            locked = Adventure.objects.select_for_update().get(id=adventure.id)
            if locked.is_waiting_ai:
                return Response(
                    {"detail": "Model response is already in progress."},
                    status=status.HTTP_409_CONFLICT,
                )
            min_id = locked.rollback_min_history_id
            target = AdventureHistory.objects.filter(adventure=adventure, id=entry_id).first()
            if target is None:
                return Response({"detail": "History entry not found."}, status=status.HTTP_404_NOT_FOUND)
            if min_id is not None and target.id < min_id:
                return Response(
                    {"detail": "Rollback is not allowed for this entry."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            entries_to_delete = list(
                AdventureHistory.objects.filter(adventure=adventure, id__gt=target.id).order_by("id")
            )
            revert_analysis_for_history_entries(adventure, entries_to_delete)
            deleted, _ = AdventureHistory.objects.filter(
                adventure=adventure, id__gt=target.id
            ).delete()
        return Response({"deleted": deleted}, status=status.HTTP_200_OK)


class AdventureRunHistoryRegenerateView(AdventureRunMixin, APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, run_id):
        adventure = self.get_adventure()
        if adventure.started_at is None:
            return Response({"detail": "Adventure not started."}, status=status.HTTP_400_BAD_REQUEST)
        include_npcs = False
        with transaction.atomic():
            locked = Adventure.objects.select_for_update().get(id=adventure.id)
            if locked.is_waiting_ai:
                return Response(
                    {"detail": "Model response is already in progress."},
                    status=status.HTTP_409_CONFLICT,
                )
            last_entry = AdventureHistory.objects.filter(adventure=adventure).order_by("-id").first()
            if last_entry is None:
                return Response({"detail": "History is empty."}, status=status.HTTP_400_BAD_REQUEST)
            min_id = locked.rollback_min_history_id
            if min_id is not None and last_entry.id < min_id:
                return Response(
                    {"detail": "Regeneration is not allowed for this entry."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if last_entry.role != AdventureHistory.Role.AI:
                return Response(
                    {"detail": "Last entry is not generated by AI."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            include_npcs = bool(last_entry.metadata.get("include_npcs"))
            npc_entry_id = last_entry.metadata.get("npc_entry_id")
            entries_to_delete = [last_entry]
            if npc_entry_id:
                npc_entry = AdventureHistory.objects.filter(
                    adventure=adventure,
                    id=npc_entry_id,
                ).first()
                if npc_entry is not None:
                    entries_to_delete.append(npc_entry)
            revert_analysis_for_history_entries(adventure, entries_to_delete)
            last_entry.delete()
            if npc_entry_id:
                AdventureHistory.objects.filter(adventure=adventure, id=npc_entry_id).delete()
        entry, npc_entry, error_data, error_status = _generate_ai_entry(
            adventure,
            include_npcs=include_npcs,
            exclude_user_id=request.user.id,
        )
        if error_data:
            return Response(error_data, status=error_status)
        return Response(
            {
                "npc_entry": AdventureHistorySerializer(npc_entry).data if npc_entry else None,
                "ai_entry": AdventureHistorySerializer(entry).data,
            },
            status=status.HTTP_201_CREATED,
        )
