"""Views for running adventures (non-template gameplay)."""
from __future__ import annotations

from io import BytesIO
import os
import secrets

from django.db import transaction
from django.db.models import Prefetch, Q
from django.http import HttpResponse
from django.utils import timezone
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from rest_framework import generics, permissions, status
from rest_framework.permissions import SAFE_METHODS
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from .ai_views import (
    _create_user_history_entry,
    _finalize_user_turn,
    _generate_ai_entry,
    format_player_move_content,
)
from .base import AdventureRunMixin, AdventureTemplateMixin
from ..services.localization import get_string, get_user_locale
from ..services.orchestrator import after_user_turn, before_user_turn
from ..models import (
    Adventure,
    AdventureEvent,
    AdventureHeroSetup,
    AdventureHistory,
    AdventurePlayer,
    Character,
    CharacterSystem,
    CharacterTechnique,
    Faction,
    LearningObjective,
    Location,
    ModerationEntry,
    PedagogicalIntervention,
    PublishedAdventure,
    OtherInfo,
    Race,
    ReflectionPrompt,
    SkillSystem,
    Technique,
)
from ..serializers import (
    AdventureHeroSetupSerializer,
    AdventureHistorySerializer,
    AdventurePlayerSerializer,
    AdventureRunSerializer,
    AdventureRunDetailSerializer,
    CharacterSerializer,
    LocationSerializer,
    RaceSerializer,
    SkillSystemSerializer,
    TechniqueSerializer,
)
from ..ws_utils import broadcast_history_entries, broadcast_lobby_state


class AdventureRunListView(generics.ListAPIView):
    serializer_class = AdventureRunSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return (
            Adventure.objects.filter(is_template=False)
            .filter(
                Q(player_user=self.request.user) | Q(players__user=self.request.user)
            )
            .distinct()
            .order_by("-created_at")
        )


class AdventureRunDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = AdventureRunDetailSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        base_queryset = Adventure.objects.filter(is_template=False)
        if self.request.method in SAFE_METHODS:
            return (
                base_queryset.filter(
                    Q(player_user=self.request.user) | Q(players__user=self.request.user)
                )
                .distinct()
            )
        return base_queryset.filter(player_user=self.request.user)

    def perform_update(self, serializer):
        adventure = serializer.save()
        primary_heroes = list(adventure.primary_heroes.all())
        if not primary_heroes and adventure.primary_hero_id:
            primary_heroes = [adventure.primary_hero]
        for character in primary_heroes:
            update_fields = []
            if not character.is_player:
                character.is_player = True
                update_fields.append("is_player")
            if not character.in_party:
                character.in_party = True
                update_fields.append("in_party")
            if update_fields:
                character.save(update_fields=update_fields)


class AdventureRunBootstrapView(AdventureRunMixin, APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, run_id):
        adventure = self.get_adventure()
        locations = LocationSerializer(
            Location.objects.filter(adventure=adventure).order_by("title"), many=True
        ).data
        races = RaceSerializer(Race.objects.filter(adventure=adventure).order_by("title"), many=True).data
        systems = SkillSystemSerializer(
            SkillSystem.objects.filter(adventure=adventure).order_by("title"), many=True
        ).data
        techniques = TechniqueSerializer(
            Technique.objects.filter(system__adventure=adventure).order_by("title"), many=True
        ).data
        setup, _ = AdventureHeroSetup.objects.get_or_create(adventure=adventure)
        player_slot = self.get_player_slot()
        available_heroes = _build_available_heroes(adventure, include_all=False)
        available_npc_heroes = _build_available_heroes(adventure, include_all=True)
        return Response(
            {
                "adventure": AdventureRunSerializer(adventure).data,
                "locations": locations,
                "races": races,
                "systems": systems,
                "techniques": techniques,
                "hero_setup": AdventureHeroSetupSerializer(setup).data,
                "shared_location": LocationSerializer(adventure.shared_location).data
                if adventure.shared_location
                else None,
                "player_slot": AdventurePlayerSerializer(player_slot).data if player_slot else None,
                "available_heroes": available_heroes,
                "available_npc_heroes": available_npc_heroes,
            }
        )


class AdventureRunStartView(AdventureTemplateMixin, APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, template_id):
        template = Adventure.objects.filter(id=template_id, is_template=True).first()
        if not template:
            raise PermissionDenied("Шаблон приключения не найден.")
        if template.author_user_id != request.user.id:
            if ModerationEntry.objects.filter(adventure=template).exists():
                raise PermissionDenied("Приключение еще на модерации.")
            if not PublishedAdventure.objects.filter(adventure=template).exists():
                raise PermissionDenied("Недостаточно прав для запуска приключения.")
        with transaction.atomic():
            template_setup, _ = AdventureHeroSetup.objects.get_or_create(adventure=template)
            run = Adventure.objects.create(
                author_user=template.author_user,
                player_user=request.user,
                template_adventure=template,
                is_template=False,
                title=template.title,
                description=template.description,
                intro=template.intro,
                spec_instructions=template.spec_instructions,
                story_locale=template.story_locale,
                facilitator_enabled=template.facilitator_enabled,
                story_simple_language=template.story_simple_language,
                story_reduced_text_length=template.story_reduced_text_length,
                growth_analysis_enabled=template.growth_analysis_enabled,
                narrative_consequences_enabled=template.narrative_consequences_enabled,
                invite_token=secrets.token_urlsafe(16),
            )
            AdventurePlayer.objects.create(
                adventure=run,
                user=request.user,
                slot_number=1,
            )

            location_map = {}
            for location in Location.objects.filter(adventure=template).order_by("title"):
                location_map[location.id] = Location.objects.create(
                    adventure=run,
                    title=location.title,
                    description=location.description,
                    x=location.x,
                    y=location.y,
                    width=location.width,
                    height=location.height,
                    tags=list(location.tags),
                )

            race_map = {}
            for race in Race.objects.filter(adventure=template).order_by("title"):
                race_map[race.id] = Race.objects.create(
                    adventure=run,
                    title=race.title,
                    description=race.description,
                    life_span=race.life_span,
                    tags=list(race.tags),
                )

            AdventureHeroSetup.objects.update_or_create(
                adventure=run,
                defaults={
                    "default_location": location_map.get(template_setup.default_location_id),
                    "require_race": template_setup.require_race,
                    "default_race": race_map.get(template_setup.default_race_id),
                    "require_age": template_setup.require_age,
                    "default_age": template_setup.default_age,
                    "require_body_power": template_setup.require_body_power,
                    "default_body_power": template_setup.default_body_power,
                    "require_mind_power": template_setup.require_mind_power,
                    "default_mind_power": template_setup.default_mind_power,
                    "require_will_power": template_setup.require_will_power,
                    "default_will_power": template_setup.default_will_power,
                    "require_systems": template_setup.require_systems,
                    "require_techniques": template_setup.require_techniques,
                },
            )
            if template_setup.default_location_id:
                run.shared_location = location_map.get(template_setup.default_location_id)
                run.save(update_fields=["shared_location"])

            system_map = {}
            for system in SkillSystem.objects.filter(adventure=template).order_by("title"):
                system_map[system.id] = SkillSystem.objects.create(
                    adventure=run,
                    title=system.title,
                    description=system.description,
                    tags=list(system.tags),
                    w_body=system.w_body,
                    w_mind=system.w_mind,
                    w_will=system.w_will,
                    formula_hint=system.formula_hint,
                )

            technique_map = {}
            for technique in Technique.objects.filter(system__adventure=template).order_by("title"):
                system = system_map.get(technique.system_id)
                if system is None:
                    continue
                technique_map[technique.id] = Technique.objects.create(
                    system=system,
                    title=technique.title,
                    description=technique.description,
                    tags=list(technique.tags),
                    difficulty=technique.difficulty,
                    tier=technique.tier,
                    required_system_level=technique.required_system_level,
                )

            for faction in Faction.objects.filter(adventure=template).order_by("title"):
                Faction.objects.create(
                    adventure=run,
                    title=faction.title,
                    description=faction.description,
                    tags=list(faction.tags),
                )

            for info in OtherInfo.objects.filter(adventure=template).order_by("title"):
                OtherInfo.objects.create(
                    adventure=run,
                    category=info.category,
                    title=info.title,
                    description=info.description,
                    tags=list(info.tags),
                )

            for event in AdventureEvent.objects.filter(adventure=template).order_by("title"):
                AdventureEvent.objects.create(
                    adventure=run,
                    title=event.title,
                    status=event.status,
                    trigger_hint=event.trigger_hint,
                    state=event.state,
                    location=location_map.get(event.location_id),
                )

            objective_map = {}
            for objective in LearningObjective.objects.filter(adventure=template).order_by("id"):
                objective_map[objective.id] = LearningObjective.objects.create(
                    adventure=run,
                    code=objective.code,
                    title=objective.title,
                    description=objective.description,
                    competency=objective.competency,
                    weight=objective.weight,
                    is_active=objective.is_active,
                )
            for prompt in ReflectionPrompt.objects.filter(adventure=template).order_by("id"):
                objective = objective_map.get(prompt.objective_id)
                if objective is None:
                    continue
                ReflectionPrompt.objects.create(
                    adventure=run,
                    objective=objective,
                    trigger_kind=prompt.trigger_kind,
                    question=prompt.question,
                    is_active=prompt.is_active,
                )
            for intervention in PedagogicalIntervention.objects.filter(adventure=template).order_by("id"):
                objective = objective_map.get(intervention.objective_id)
                if objective is None:
                    continue
                PedagogicalIntervention.objects.create(
                    adventure=run,
                    objective=objective,
                    kind=intervention.kind,
                    payload=intervention.payload,
                    is_active=intervention.is_active,
                )

            character_map = {}
            for character in Character.objects.filter(adventure=template).order_by("title"):
                character_map[character.id] = Character.objects.create(
                    adventure=run,
                    title=character.title,
                    description=character.description,
                    is_player=character.is_player,
                    in_party=character.in_party,
                    story_status=character.story_status,
                    age=character.age,
                    body_power=character.body_power,
                    body_power_progress=character.body_power_progress,
                    mind_power=character.mind_power,
                    mind_power_progress=character.mind_power_progress,
                    will_power=character.will_power,
                    will_power_progress=character.will_power_progress,
                    tags=list(character.tags),
                    race=race_map.get(character.race_id),
                    location=location_map.get(character.location_id),
                )

            for entry in CharacterSystem.objects.filter(
                character__adventure=template
            ).order_by("id"):
                character = character_map.get(entry.character_id)
                system = system_map.get(entry.system_id)
                if character is None or system is None:
                    continue
                CharacterSystem.objects.create(
                    character=character,
                    system=system,
                    level=entry.level,
                    progress_percent=entry.progress_percent,
                    notes=entry.notes,
                )

            for entry in CharacterTechnique.objects.filter(
                character__adventure=template
            ).order_by("id"):
                character = character_map.get(entry.character_id)
                technique = technique_map.get(entry.technique_id)
                if character is None or technique is None:
                    continue
                CharacterTechnique.objects.create(
                    character=character,
                    technique=technique,
                    notes=entry.notes,
                )

            primary_hero_ids = list(template.primary_heroes.values_list("id", flat=True))
            if not primary_hero_ids and template.primary_hero_id:
                primary_hero_ids = [template.primary_hero_id]
            primary_heroes = [
                character_map[hero_id]
                for hero_id in primary_hero_ids
                if hero_id in character_map
            ]
            if primary_heroes:
                run.primary_heroes.set(primary_heroes)

        return Response(AdventureRunSerializer(run).data, status=status.HTTP_201_CREATED)


def _ensure_invite_token(adventure: Adventure) -> str:
    if adventure.invite_token:
        return adventure.invite_token
    token = secrets.token_urlsafe(16)
    Adventure.objects.filter(id=adventure.id).update(invite_token=token)
    adventure.invite_token = token
    return token


def _next_available_slot(adventure: Adventure) -> int | None:
    taken = set(
        AdventurePlayer.objects.filter(adventure=adventure).values_list("slot_number", flat=True)
    )
    for slot in range(1, adventure.max_players + 1):
        if slot not in taken:
            return slot
    return None


def _primary_hero_ids(adventure: Adventure) -> set[int]:
    primary_ids = set(adventure.primary_heroes.values_list("id", flat=True))
    if not primary_ids and adventure.primary_hero_id:
        primary_ids.add(adventure.primary_hero_id)
    return primary_ids


def _build_available_heroes(adventure: Adventure, include_all: bool = False) -> list[dict]:
    taken_ids = set(
        AdventurePlayer.objects.filter(adventure=adventure, hero__isnull=False).values_list(
            "hero_id", flat=True
        )
    )
    primary_ids = _primary_hero_ids(adventure)
    queryset = Character.objects.filter(adventure=adventure)
    if not include_all:
        queryset = queryset.filter(is_player=True)
    heroes = []
    for hero in queryset.order_by("title"):
        heroes.append(
            {
                "id": hero.id,
                "title": hero.title,
                "is_primary": hero.id in primary_ids,
                "is_taken": hero.id in taken_ids,
                "is_player": hero.is_player,
            }
        )
    return heroes


def _can_start_adventure(adventure: Adventure) -> bool:
    players = AdventurePlayer.objects.filter(adventure=adventure)
    if not players.exists():
        return False
    if players.filter(hero__isnull=True).exists():
        return False
    primary_ids = _primary_hero_ids(adventure)
    if primary_ids:
        taken_ids = set(players.values_list("hero_id", flat=True))
        return all(hero_id in taken_ids for hero_id in primary_ids)
    return True


def _build_lobby_payload(adventure: Adventure) -> dict:
    players = (
        AdventurePlayer.objects.filter(adventure=adventure)
        .select_related("user", "hero")
        .order_by("slot_number")
    )
    available_heroes = _build_available_heroes(adventure, include_all=False)
    return {
        "adventure": AdventureRunSerializer(adventure).data,
        "players": AdventurePlayerSerializer(players, many=True).data,
        "available_heroes": available_heroes,
        "shared_location": LocationSerializer(adventure.shared_location).data
        if adventure.shared_location
        else None,
        "max_players": adventure.max_players,
        "invite_token": _ensure_invite_token(adventure),
        "can_start": _can_start_adventure(adventure) and adventure.started_at is None,
        "owner_id": adventure.player_user_id,
    }


class AdventureRunLobbyView(AdventureRunMixin, APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, run_id):
        adventure = self.get_adventure()
        player_slot = self.get_player_slot()
        payload = _build_lobby_payload(adventure)
        payload["player_slot"] = (
            AdventurePlayerSerializer(player_slot).data if player_slot else None
        )
        payload["is_owner"] = adventure.player_user_id == request.user.id
        return Response(payload)


class AdventureRunJoinView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, run_id):
        adventure = Adventure.objects.filter(id=run_id, is_template=False).first()
        if adventure is None:
            return Response({"detail": "Adventure not found."}, status=status.HTTP_404_NOT_FOUND)
        if adventure.started_at is not None:
            return Response({"detail": "Adventure already started."}, status=status.HTTP_400_BAD_REQUEST)
        payload = request.data or {}
        token = payload.get("token")
        if not token or token != adventure.invite_token:
            return Response({"detail": "Invalid invite token."}, status=status.HTTP_403_FORBIDDEN)
        existing = AdventurePlayer.objects.filter(
            adventure=adventure, user=request.user
        ).first()
        if existing:
            return Response(AdventurePlayerSerializer(existing).data, status=status.HTTP_200_OK)
        with transaction.atomic():
            locked = Adventure.objects.select_for_update().get(id=adventure.id)
            slot = _next_available_slot(locked)
            if slot is None:
                return Response({"detail": "No free slots."}, status=status.HTTP_409_CONFLICT)
            player = AdventurePlayer.objects.create(
                adventure=locked,
                user=request.user,
                slot_number=slot,
            )
        broadcast_lobby_state(
            adventure.id,
            _build_lobby_payload(adventure),
            exclude_user_id=request.user.id,
        )
        return Response(AdventurePlayerSerializer(player).data, status=status.HTTP_201_CREATED)


class AdventureRunStartLobbyView(AdventureRunMixin, APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, run_id):
        adventure = self.get_adventure()
        if adventure.player_user_id != request.user.id:
            raise PermissionDenied("Недостаточно прав для запуска приключения.")
        if adventure.started_at is not None:
            return Response(AdventureRunSerializer(adventure).data, status=status.HTTP_200_OK)
        if not _can_start_adventure(adventure):
            return Response({"detail": "Adventure is not ready."}, status=status.HTTP_400_BAD_REQUEST)
        adventure.started_at = timezone.now()
        adventure.save(update_fields=["started_at"])
        primary_heroes = list(adventure.primary_heroes.all().order_by("title"))
        if not primary_heroes and adventure.primary_hero_id:
            primary_heroes = [adventure.primary_hero]
        if primary_heroes and adventure.intro:
            hero_names = ", ".join(hero.title for hero in primary_heroes)
            intro_text = adventure.intro.replace("<main_hero>", hero_names)
            if not AdventureHistory.objects.filter(adventure=adventure).exists():
                AdventureHistory.objects.create(
                    adventure=adventure,
                    role=AdventureHistory.Role.SYSTEM,
                    content=intro_text,
                    metadata={},
                )
        broadcast_lobby_state(
            adventure.id,
            _build_lobby_payload(adventure),
            exclude_user_id=request.user.id,
        )
        return Response(AdventureRunSerializer(adventure).data, status=status.HTTP_200_OK)


def _resolve_shared_location(
    adventure: Adventure, setup: AdventureHeroSetup, payload: dict
) -> tuple[Location | None, str | None]:
    location_id = payload.get("location_id")
    location_title = (payload.get("location_title") or "").strip()
    if adventure.shared_location:
        return adventure.shared_location, None
    if setup.default_location:
        adventure.shared_location = setup.default_location
        adventure.save(update_fields=["shared_location"])
        return setup.default_location, None
    if location_id is None and not location_title:
        return None, "Location is required."
    if location_id is not None:
        location = Location.objects.filter(adventure=adventure, id=location_id).first()
        if location is None:
            return None, "Location not found."
    else:
        location = Location.objects.create(
            adventure=adventure,
            title=location_title,
            description=payload.get("location_description", ""),
            x=0,
            y=0,
            width=1,
            height=1,
            tags=[],
        )
    adventure.shared_location = location
    adventure.save(update_fields=["shared_location"])
    return location, None


def _assign_existing_hero_to_slot(
    adventure: Adventure,
    slot: AdventurePlayer,
    hero_id: int,
    location: Location,
    require_player: bool,
) -> tuple[Character | None, str | None, int | None]:
    hero = Character.objects.filter(adventure=adventure, id=hero_id).first()
    if hero is None or (require_player and not hero.is_player):
        return None, "Hero not found.", status.HTTP_400_BAD_REQUEST
    if (
        AdventurePlayer.objects.filter(adventure=adventure, hero=hero)
        .exclude(id=slot.id)
        .exists()
    ):
        return None, "Герой уже выбран другим игроком.", status.HTTP_409_CONFLICT
    update_fields = []
    if hero.location_id != location.id:
        hero.location = location
        update_fields.append("location")
    if not hero.in_party:
        hero.in_party = True
        update_fields.append("in_party")
    if update_fields:
        hero.save(update_fields=update_fields)
    slot.hero = hero
    slot.save(update_fields=["hero"])
    return hero, None, None


def _create_hero_for_slot(
    adventure: Adventure,
    slot: AdventurePlayer,
    payload: dict,
    setup: AdventureHeroSetup,
    location: Location,
    is_player: bool,
) -> tuple[Character | None, str | None, int | None]:
    hero_data = payload.get("hero", {}) or {}
    system_entries = payload.get("systems", []) or []
    technique_entries = payload.get("techniques", []) or []
    if setup.require_race and hero_data.get("race") is None:
        return None, "Race is required.", status.HTTP_400_BAD_REQUEST
    if setup.require_age and hero_data.get("age") is None:
        return None, "Age is required.", status.HTTP_400_BAD_REQUEST
    if setup.require_body_power and hero_data.get("body_power") is None:
        return None, "Body power is required.", status.HTTP_400_BAD_REQUEST
    if setup.require_mind_power and hero_data.get("mind_power") is None:
        return None, "Mind power is required.", status.HTTP_400_BAD_REQUEST
    if setup.require_will_power and hero_data.get("will_power") is None:
        return None, "Will power is required.", status.HTTP_400_BAD_REQUEST
    if not hero_data:
        return None, "Нужны данные героя.", status.HTTP_400_BAD_REQUEST

    validated_systems = []
    if system_entries:
        for entry in system_entries:
            system = SkillSystem.objects.filter(
                adventure=adventure, id=entry.get("system")
            ).first()
            if system is None:
                return None, "System not found.", status.HTTP_400_BAD_REQUEST
            validated_systems.append((system, entry))

    validated_techniques = []
    if technique_entries:
        for entry in technique_entries:
            technique = Technique.objects.filter(
                system__adventure=adventure, id=entry.get("technique")
            ).first()
            if technique is None:
                return None, "Technique not found.", status.HTTP_400_BAD_REQUEST
            validated_techniques.append((technique, entry))

    race_id = hero_data.get("race")
    race = None
    if race_id is not None:
        race = Race.objects.filter(adventure=adventure, id=race_id).first()
        if race is None:
            return None, "Race not found.", status.HTTP_400_BAD_REQUEST
    elif not setup.require_race:
        race = setup.default_race

    age = hero_data.get("age")
    if age is None and not setup.require_age:
        age = setup.default_age

    body_power = hero_data.get("body_power")
    if body_power is None and not setup.require_body_power:
        body_power = setup.default_body_power if setup.default_body_power is not None else 0

    mind_power = hero_data.get("mind_power")
    if mind_power is None and not setup.require_mind_power:
        mind_power = setup.default_mind_power if setup.default_mind_power is not None else 0

    will_power = hero_data.get("will_power")
    if will_power is None and not setup.require_will_power:
        will_power = setup.default_will_power if setup.default_will_power is not None else 0

    with transaction.atomic():
        hero = Character.objects.create(
            adventure=adventure,
            title=hero_data.get("title", "Hero"),
            description=hero_data.get("description", ""),
            is_player=is_player,
            in_party=True,
            age=age,
            body_power=body_power if body_power is not None else 0,
            body_power_progress=0,
            mind_power=mind_power if mind_power is not None else 0,
            mind_power_progress=0,
            will_power=will_power if will_power is not None else 0,
            will_power_progress=0,
            tags=hero_data.get("tags", []) or [],
            race=race,
            location=location,
        )

        if validated_systems:
            for system, entry in validated_systems:
                CharacterSystem.objects.create(
                    character=hero,
                    system=system,
                    level=entry.get("level", 0),
                    progress_percent=entry.get("progress_percent", 0),
                    notes=entry.get("notes", ""),
                )

        if validated_techniques:
            for technique, entry in validated_techniques:
                CharacterTechnique.objects.create(
                    character=hero,
                    technique=technique,
                    notes=entry.get("notes", ""),
                )

        slot.hero = hero
        slot.save(update_fields=["hero"])

    return hero, None, None


class AdventureRunHeroSetupView(AdventureRunMixin, APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, run_id):
        adventure = self.get_adventure()
        player_slot = self.get_player_slot()
        if player_slot is None:
            raise PermissionDenied("Недостаточно прав для доступа к приключению.")
        if adventure.started_at is not None:
            return Response({"detail": "Adventure already started."}, status=status.HTTP_400_BAD_REQUEST)
        if player_slot.hero_id:
            return Response({"detail": "Герой уже выбран."}, status=status.HTTP_400_BAD_REQUEST)
        payload = request.data or {}
        hero_id = payload.get("hero_id")
        setup, _ = AdventureHeroSetup.objects.get_or_create(adventure=adventure)

        location, error = _resolve_shared_location(adventure, setup, payload)
        if error:
            return Response({"detail": error}, status=status.HTTP_400_BAD_REQUEST)

        if hero_id is not None:
            hero, error, error_status = _assign_existing_hero_to_slot(
                adventure, player_slot, hero_id, location, True
            )
            if error:
                return Response({"detail": error}, status=error_status)
            broadcast_lobby_state(
                adventure.id,
                _build_lobby_payload(adventure),
                exclude_user_id=request.user.id,
            )
            return Response({"hero_id": hero.id}, status=status.HTTP_201_CREATED)

        hero, error, error_status = _create_hero_for_slot(
            adventure, player_slot, payload, setup, location, True
        )
        if error:
            return Response({"detail": error}, status=error_status)

        broadcast_lobby_state(
            adventure.id,
            _build_lobby_payload(adventure),
            exclude_user_id=request.user.id,
        )
        return Response({"hero_id": hero.id}, status=status.HTTP_201_CREATED)


class AdventureRunNpcSlotView(AdventureRunMixin, APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, run_id, slot_number):
        adventure = self.get_adventure()
        if adventure.player_user_id != request.user.id:
            raise PermissionDenied("Недостаточно прав для доступа к приключению.")
        if adventure.started_at is not None:
            return Response({"detail": "Adventure already started."}, status=status.HTTP_400_BAD_REQUEST)
        if slot_number < 1 or slot_number > adventure.max_players:
            return Response({"detail": "Slot number out of range."}, status=status.HTTP_400_BAD_REQUEST)

        payload = request.data or {}
        hero_id = payload.get("hero_id")
        hero_data = payload.get("hero", {}) or {}

        response_body = None
        response_status = None
        should_broadcast = False
        with transaction.atomic():
            locked = Adventure.objects.select_for_update().get(id=adventure.id)
            slot = (
                AdventurePlayer.objects.select_for_update()
                .filter(adventure=locked, slot_number=slot_number)
                .first()
            )
            if slot and not slot.is_npc:
                return Response(
                    {"detail": "Slot is already taken by a player."},
                    status=status.HTTP_409_CONFLICT,
                )
            if slot is None:
                slot = AdventurePlayer.objects.create(
                    adventure=locked,
                    slot_number=slot_number,
                    is_npc=True,
                    wrote_after_ai=True,
                )
                should_broadcast = True
            elif slot.is_npc and not slot.wrote_after_ai:
                slot.wrote_after_ai = True
                slot.save(update_fields=["wrote_after_ai"])
            if slot.hero_id and (hero_id is not None or hero_data):
                return Response({"detail": "Герой уже выбран."}, status=status.HTTP_400_BAD_REQUEST)
            if hero_id is None and not hero_data:
                response_body = AdventurePlayerSerializer(slot).data
                response_status = status.HTTP_200_OK
            else:
                setup, _ = AdventureHeroSetup.objects.get_or_create(adventure=locked)
                location, error = _resolve_shared_location(locked, setup, payload)
                if error:
                    return Response({"detail": error}, status=status.HTTP_400_BAD_REQUEST)

                if hero_id is not None:
                    hero, error, error_status = _assign_existing_hero_to_slot(
                        locked, slot, hero_id, location, False
                    )
                else:
                    hero, error, error_status = _create_hero_for_slot(
                        locked, slot, payload, setup, location, False
                    )
                if error:
                    return Response({"detail": error}, status=error_status)
                response_body = {"hero_id": hero.id}
                response_status = status.HTTP_201_CREATED
                should_broadcast = True

        if should_broadcast:
            broadcast_lobby_state(
                adventure.id,
                _build_lobby_payload(adventure),
                exclude_user_id=request.user.id,
            )
        return Response(response_body, status=response_status)


class AdventureRunHistoryView(AdventureRunMixin, generics.ListAPIView):
    serializer_class = AdventureHistorySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return AdventureHistory.objects.filter(adventure=self.get_adventure()).order_by("id")

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
        if player_slot is None:
            raise PermissionDenied("Недостаточно прав для доступа к приключению.")
        payload = request.data or {}
        content = (payload.get("content") or "").strip()
        hero_state = (payload.get("hero_state") or "").strip()
        if not content:
            return Response({"detail": "Content is required."}, status=status.HTTP_400_BAD_REQUEST)
        entry_content = format_player_move_content(
            content,
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
                AdventureHistorySerializer(user_entry).data,
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


class AdventureRunPassView(AdventureRunMixin, APIView):
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
        if player_slot is None:
            raise PermissionDenied("Недостаточно прав для доступа к приключению.")
        if not player_slot.wrote_after_ai:
            player_slot.wrote_after_ai = True
            player_slot.save(update_fields=["wrote_after_ai"])
        if AdventurePlayer.objects.filter(
            adventure=adventure, wrote_after_ai=False, is_npc=False
        ).exists():
            return Response({"detail": "Pass accepted."}, status=status.HTTP_200_OK)
        ai_entry, npc_entry, error_data, _ = _generate_ai_entry(
            adventure,
            include_npcs=True,
            exclude_user_id=request.user.id,
        )
        if error_data:
            return Response(
                {"detail": error_data.get("detail"), "ai_entry": None},
                status=status.HTTP_201_CREATED,
            )
        return Response(
            {
                "npc_entry": AdventureHistorySerializer(npc_entry).data if npc_entry else None,
                "ai_entry": AdventureHistorySerializer(ai_entry).data if ai_entry else None,
            },
            status=status.HTTP_201_CREATED,
        )


class AdventureRunHistoryPdfView(AdventureRunMixin, APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, run_id):
        adventure = self.get_adventure()
        history_entries = AdventureHistory.objects.filter(adventure=adventure).order_by("id")
        heroes = (
            Character.objects.filter(player_slots__adventure=adventure)
            .distinct()
            .order_by("title")
        )

        buffer = BytesIO()
        pdf = canvas.Canvas(buffer, pagesize=A4)
        font_name = "Helvetica"
        font_size = 11
        font_path = os.getenv(
            "PDF_FONT_PATH",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        )
        if os.path.exists(font_path):
            try:
                pdfmetrics.registerFont(TTFont("DejaVuSans", font_path))
                font_name = "DejaVuSans"
            except Exception:
                font_name = "Helvetica"
        width, height = A4
        left_margin = 48
        top = height - 54
        line_height = 14

        def set_font():
            pdf.setFont(font_name, font_size)

        def write_line(text, current_y):
            set_font()
            pdf.drawString(left_margin, current_y, text)
            return current_y - line_height

        def wrap_text(text, max_width):
            paragraphs = text.splitlines() or [""]
            lines = []
            for paragraph in paragraphs:
                words = paragraph.split()
                if not words:
                    lines.append("")
                    continue
                current = ""
                for word in words:
                    test = f"{current} {word}".strip()
                    if pdfmetrics.stringWidth(test, font_name, font_size) <= max_width:
                        current = test
                    else:
                        if current:
                            lines.append(current)
                        current = word
                if current:
                    lines.append(current)
            return lines

        y = top
        y = write_line(f"Приключение: {adventure.title}", y)
        hero_names = ", ".join(hero.title for hero in heroes) or "—"
        y = write_line(f"Главные герои: {hero_names}", y)
        y = write_line("История:", y - line_height)

        max_width = width - left_margin * 2
        for entry in history_entries:
            role_label = entry.role
            header = f"{role_label.upper()}:"
            if y < 72:
                pdf.showPage()
                y = top
                set_font()
            y = write_line(header, y)
            for line in wrap_text(entry.content or "", max_width):
                if y < 72:
                    pdf.showPage()
                    y = top
                    set_font()
                if line == "":
                    y -= line_height
                else:
                    y = write_line(line, y)
            y -= line_height / 2

        pdf.showPage()
        pdf.save()
        buffer.seek(0)
        response = HttpResponse(buffer, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="adventure_{adventure.id}_history.pdf"'
        return response


class AdventureRunCharactersView(AdventureRunMixin, generics.ListAPIView):
    serializer_class = CharacterSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return (
            Character.objects.filter(
                adventure=self.get_adventure(),
                in_party=True,
                story_status=Character.StoryStatus.ACTIVE,
            )
            .prefetch_related(
                Prefetch(
                    "player_slots",
                    queryset=AdventurePlayer.objects.select_related("user"),
                )
            )
            .order_by("title")
        )
