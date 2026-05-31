"""Views for exporting and importing adventure templates."""
from __future__ import annotations

import logging

from django.db import transaction
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from backend.llm import get_llm_client

from .base import AdventureTemplateMixin
from ..models import (
    Adventure,
    AdventureEvent,
    AdventureHeroSetup,
    Character,
    CharacterSystem,
    CharacterTechnique,
    Faction,
    LearningObjective,
    Location,
    OtherInfo,
    PedagogicalIntervention,
    Race,
    ReflectionPrompt,
    SkillSystem,
    Technique,
)
from ..serializers import AdventureTemplateSerializer
from ..services.template_translation import TemplateTranslationError, clone_translated_template


logger = logging.getLogger(__name__)


def _build_export_list(queryset, fields):
    export_id_map = {}
    items = []
    for index, item in enumerate(queryset, start=1):
        export_id = str(index)
        export_id_map[item.id] = export_id
        payload = {"export_id": export_id}
        for field in fields:
            payload[field] = getattr(item, field)
        items.append((item, payload))
    return items, export_id_map


def _parse_bool(value) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)


def _parse_story_locale(value) -> str:
    return value if value in Adventure.StoryLocale.values else Adventure.StoryLocale.RU


class AdventureTemplateExportView(AdventureTemplateMixin, APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, template_id):
        adventure = self.get_adventure()

        locations, location_map = _build_export_list(
            Location.objects.filter(adventure=adventure).order_by("title"),
            ["title", "description", "x", "y", "width", "height", "tags"],
        )
        races, race_map = _build_export_list(
            Race.objects.filter(adventure=adventure).order_by("title"),
            ["title", "description", "life_span", "tags"],
        )
        systems, system_map = _build_export_list(
            SkillSystem.objects.filter(adventure=adventure).order_by("title"),
            ["title", "description", "tags", "w_body", "w_mind", "w_will", "formula_hint"],
        )
        techniques, technique_map = _build_export_list(
            Technique.objects.filter(system__adventure=adventure).order_by("title"),
            ["title", "description", "tags", "difficulty", "tier", "required_system_level"],
        )
        factions, faction_map = _build_export_list(
            Faction.objects.filter(adventure=adventure).order_by("title"),
            ["title", "description", "tags"],
        )
        other_info, other_info_map = _build_export_list(
            OtherInfo.objects.filter(adventure=adventure).order_by("title"),
            ["category", "title", "description", "tags"],
        )
        characters, character_map = _build_export_list(
            Character.objects.filter(adventure=adventure).order_by("title"),
            [
                "title",
                "description",
                "is_player",
                "in_party",
                "story_status",
                "age",
                "body_power",
                "body_power_progress",
                "mind_power",
                "mind_power_progress",
                "will_power",
                "will_power_progress",
                "tags",
            ],
        )

        for character, entry in characters:
            entry["race"] = race_map.get(character.race_id)
            entry["location"] = location_map.get(character.location_id)

        for technique, entry in techniques:
            entry["system"] = system_map.get(technique.system_id)

        events, event_map = _build_export_list(
            AdventureEvent.objects.filter(adventure=adventure).order_by("title"),
            ["title", "status", "trigger_hint", "state"],
        )
        for event, entry in events:
            entry["location"] = location_map.get(event.location_id)

        learning_objectives, objective_map = _build_export_list(
            LearningObjective.objects.filter(adventure=adventure).order_by("id"),
            ["code", "title", "description", "competency", "weight", "is_active"],
        )
        reflection_prompts, _ = _build_export_list(
            ReflectionPrompt.objects.filter(adventure=adventure).order_by("id"),
            ["trigger_kind", "question", "is_active"],
        )
        for prompt, entry in reflection_prompts:
            entry["objective"] = objective_map.get(prompt.objective_id)

        pedagogical_interventions, _ = _build_export_list(
            PedagogicalIntervention.objects.filter(adventure=adventure).order_by("id"),
            ["kind", "payload", "is_active"],
        )
        for intervention, entry in pedagogical_interventions:
            entry["objective"] = objective_map.get(intervention.objective_id)

        character_systems = []
        for entry in CharacterSystem.objects.filter(
            character__adventure=adventure
        ).order_by("id"):
            character_systems.append(
                {
                    "character": character_map.get(entry.character_id),
                    "system": system_map.get(entry.system_id),
                    "level": entry.level,
                    "progress_percent": entry.progress_percent,
                    "notes": entry.notes,
                }
            )

        character_techniques = []
        for entry in CharacterTechnique.objects.filter(
            character__adventure=adventure
        ).order_by("id"):
            character_techniques.append(
                {
                    "character": character_map.get(entry.character_id),
                    "technique": technique_map.get(entry.technique_id),
                    "notes": entry.notes,
                }
            )

        hero_setup, _ = AdventureHeroSetup.objects.get_or_create(adventure=adventure)

        primary_hero_ids = list(adventure.primary_heroes.values_list("id", flat=True))
        if not primary_hero_ids and adventure.primary_hero_id:
            primary_hero_ids = [adventure.primary_hero_id]
        primary_heroes_export = [
            character_map.get(hero_id)
            for hero_id in primary_hero_ids
            if hero_id in character_map
        ]
        payload = {
            "version": 5,
            "adventure": {
                "title": adventure.title,
                "description": adventure.description,
                "spec_instructions": adventure.spec_instructions,
                "intro": adventure.intro,
                "story_locale": adventure.story_locale,
                "facilitator_enabled": adventure.facilitator_enabled,
                "story_simple_language": adventure.story_simple_language,
                "story_reduced_text_length": adventure.story_reduced_text_length,
                "growth_analysis_enabled": adventure.growth_analysis_enabled,
                "narrative_consequences_enabled": adventure.narrative_consequences_enabled,
                "primary_hero": primary_heroes_export[0] if primary_heroes_export else None,
                "primary_heroes": primary_heroes_export,
            },
            "hero_setup": {
                "default_location": location_map.get(hero_setup.default_location_id),
                "require_race": hero_setup.require_race,
                "default_race": race_map.get(hero_setup.default_race_id),
                "require_age": hero_setup.require_age,
                "default_age": hero_setup.default_age,
                "require_body_power": hero_setup.require_body_power,
                "default_body_power": hero_setup.default_body_power,
                "require_mind_power": hero_setup.require_mind_power,
                "default_mind_power": hero_setup.default_mind_power,
                "require_will_power": hero_setup.require_will_power,
                "default_will_power": hero_setup.default_will_power,
                "require_systems": hero_setup.require_systems,
                "require_techniques": hero_setup.require_techniques,
            },
            "locations": [entry for _, entry in locations],
            "races": [entry for _, entry in races],
            "systems": [entry for _, entry in systems],
            "techniques": [entry for _, entry in techniques],
            "factions": [entry for _, entry in factions],
            "other_info": [entry for _, entry in other_info],
            "characters": [entry for _, entry in characters],
            "events": [entry for _, entry in events],
            "learning_objectives": [entry for _, entry in learning_objectives],
            "reflection_prompts": [entry for _, entry in reflection_prompts],
            "pedagogical_interventions": [
                entry for _, entry in pedagogical_interventions
            ],
            "character_systems": character_systems,
            "character_techniques": character_techniques,
        }
        return Response(payload)


class AdventureTemplateTranslateView(AdventureTemplateMixin, APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, template_id):
        adventure = self.get_adventure()
        target_locale = request.data.get("target_locale")
        if target_locale not in Adventure.StoryLocale.values:
            return Response(
                {"detail": "Unsupported target locale."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if target_locale == adventure.story_locale:
            return Response(
                {"detail": "The target locale must differ from the source locale."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            result = clone_translated_template(
                adventure,
                target_locale=target_locale,
                client=get_llm_client(),
                author_user=request.user,
            )
        except TemplateTranslationError as exc:
            logger.warning("Template translation failed: %s", exc)
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        except Exception:
            logger.exception("Template translation failed.")
            return Response(
                {"detail": "Template translation failed."},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        data = AdventureTemplateSerializer(
            result.template,
            context={"request": request},
        ).data
        data["translation"] = {
            "source_template_id": adventure.id,
            "target_locale": target_locale,
            "translated_fields": result.translated_fields,
            "batches": result.batches,
        }
        return Response(data, status=status.HTTP_201_CREATED)


class AdventureTemplateImportView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        data = request.data
        if not isinstance(data, dict):
            return Response({"detail": "Invalid payload."}, status=status.HTTP_400_BAD_REQUEST)

        adventure_data = data.get("adventure", {}) or {}
        hero_setup_data = data.get("hero_setup", {}) or {}
        with transaction.atomic():
            adventure = Adventure.objects.create(
                author_user=request.user,
                is_template=True,
                player_user=None,
                template_adventure=None,
                title=adventure_data.get("title", "Imported adventure"),
                description=adventure_data.get("description", ""),
                spec_instructions=adventure_data.get("spec_instructions", ""),
                intro=adventure_data.get("intro", ""),
                story_locale=_parse_story_locale(adventure_data.get("story_locale")),
                facilitator_enabled=_parse_bool(
                    adventure_data.get("facilitator_enabled", True)
                ),
                story_simple_language=_parse_bool(
                    adventure_data.get("story_simple_language", False)
                ),
                story_reduced_text_length=_parse_bool(
                    adventure_data.get("story_reduced_text_length", False)
                ),
                growth_analysis_enabled=_parse_bool(
                    adventure_data.get("growth_analysis_enabled", False)
                ),
                narrative_consequences_enabled=_parse_bool(
                    adventure_data.get("narrative_consequences_enabled", False)
                ),
            )

            location_map = {}
            for entry in data.get("locations", []) or []:
                location = Location.objects.create(
                    adventure=adventure,
                    title=entry.get("title", ""),
                    description=entry.get("description", ""),
                    x=entry.get("x", 0),
                    y=entry.get("y", 0),
                    width=entry.get("width", 1),
                    height=entry.get("height", 1),
                    tags=entry.get("tags", []) or [],
                )
                location_map[entry.get("export_id")] = location

            race_map = {}
            for entry in data.get("races", []) or []:
                race = Race.objects.create(
                    adventure=adventure,
                    title=entry.get("title", ""),
                    description=entry.get("description", ""),
                    life_span=entry.get("life_span", 100),
                    tags=entry.get("tags", []) or [],
                )
                race_map[entry.get("export_id")] = race

            system_map = {}
            for entry in data.get("systems", []) or []:
                system = SkillSystem.objects.create(
                    adventure=adventure,
                    title=entry.get("title", ""),
                    description=entry.get("description", ""),
                    tags=entry.get("tags", []) or [],
                    w_body=entry.get("w_body", 0),
                    w_mind=entry.get("w_mind", 0),
                    w_will=entry.get("w_will", 0),
                    formula_hint=entry.get("formula_hint", ""),
                )
                system_map[entry.get("export_id")] = system

            technique_map = {}
            for entry in data.get("techniques", []) or []:
                system = system_map.get(entry.get("system"))
                if system is None:
                    continue
                technique = Technique.objects.create(
                    system=system,
                    title=entry.get("title", ""),
                    description=entry.get("description", ""),
                    tags=entry.get("tags", []) or [],
                    difficulty=entry.get("difficulty", 0),
                    tier=entry.get("tier", None),
                    required_system_level=entry.get("required_system_level", 0),
                )
                technique_map[entry.get("export_id")] = technique

            for entry in data.get("factions", []) or []:
                Faction.objects.create(
                    adventure=adventure,
                    title=entry.get("title", ""),
                    description=entry.get("description", ""),
                    tags=entry.get("tags", []) or [],
                )

            for entry in data.get("other_info", []) or []:
                OtherInfo.objects.create(
                    adventure=adventure,
                    category=entry.get("category", ""),
                    title=entry.get("title", ""),
                    description=entry.get("description", ""),
                    tags=entry.get("tags", []) or [],
                )

            character_map = {}
            for entry in data.get("characters", []) or []:
                story_status = entry.get("story_status", Character.StoryStatus.ACTIVE)
                if story_status not in Character.StoryStatus.values:
                    story_status = Character.StoryStatus.ACTIVE
                character = Character.objects.create(
                    adventure=adventure,
                    title=entry.get("title", ""),
                    description=entry.get("description", ""),
                    is_player=entry.get("is_player", False),
                    in_party=entry.get("in_party", False),
                    story_status=story_status,
                    age=entry.get("age"),
                    body_power=entry.get("body_power", 0),
                    body_power_progress=entry.get("body_power_progress", 0),
                    mind_power=entry.get("mind_power", 0),
                    mind_power_progress=entry.get("mind_power_progress", 0),
                    will_power=entry.get("will_power", 0),
                    will_power_progress=entry.get("will_power_progress", 0),
                    tags=entry.get("tags", []) or [],
                    race=race_map.get(entry.get("race")),
                    location=location_map.get(entry.get("location")),
                )
                character_map[entry.get("export_id")] = character

            for entry in data.get("events", []) or []:
                AdventureEvent.objects.create(
                    adventure=adventure,
                    title=entry.get("title", ""),
                    status=entry.get("status", "inactive"),
                    trigger_hint=entry.get("trigger_hint", ""),
                    state=entry.get("state", ""),
                    location=location_map.get(entry.get("location")),
                )

            objective_map = {}
            for entry in data.get("learning_objectives", []) or []:
                objective = LearningObjective.objects.create(
                    adventure=adventure,
                    code=entry.get("code", ""),
                    title=entry.get("title", ""),
                    description=entry.get("description", ""),
                    competency=entry.get("competency", "empathy"),
                    weight=entry.get("weight", 1),
                    is_active=entry.get("is_active", True),
                )
                objective_map[entry.get("export_id")] = objective

            for entry in data.get("reflection_prompts", []) or []:
                objective = objective_map.get(entry.get("objective"))
                if objective is None:
                    continue
                ReflectionPrompt.objects.create(
                    adventure=adventure,
                    objective=objective,
                    trigger_kind=entry.get("trigger_kind", "key_choice"),
                    question=entry.get("question", ""),
                    is_active=entry.get("is_active", True),
                )

            for entry in data.get("pedagogical_interventions", []) or []:
                objective = objective_map.get(entry.get("objective"))
                if objective is None:
                    continue
                PedagogicalIntervention.objects.create(
                    adventure=adventure,
                    objective=objective,
                    kind=entry.get("kind", "dilemma"),
                    payload=entry.get("payload", {}) or {},
                    is_active=entry.get("is_active", True),
                )

            for entry in data.get("character_systems", []) or []:
                character = character_map.get(entry.get("character"))
                system = system_map.get(entry.get("system"))
                if character is None or system is None:
                    continue
                CharacterSystem.objects.create(
                    character=character,
                    system=system,
                    level=entry.get("level", 0),
                    progress_percent=entry.get("progress_percent", 0),
                    notes=entry.get("notes", ""),
                )

            for entry in data.get("character_techniques", []) or []:
                character = character_map.get(entry.get("character"))
                technique = technique_map.get(entry.get("technique"))
                if character is None or technique is None:
                    continue
                CharacterTechnique.objects.create(
                    character=character,
                    technique=technique,
                    notes=entry.get("notes", ""),
                )

            primary_hero_refs = adventure_data.get("primary_heroes") or []
            if not primary_hero_refs:
                fallback_ref = adventure_data.get("primary_hero")
                if fallback_ref:
                    primary_hero_refs = [fallback_ref]
            primary_heroes = [
                character_map[ref]
                for ref in primary_hero_refs
                if ref in character_map
            ]
            if primary_heroes:
                adventure.primary_heroes.set(primary_heroes)
                for hero in primary_heroes:
                    update_fields = []
                    if not hero.is_player:
                        hero.is_player = True
                        update_fields.append("is_player")
                    if not hero.in_party:
                        hero.in_party = True
                        update_fields.append("in_party")
                    if update_fields:
                        hero.save(update_fields=update_fields)

            AdventureHeroSetup.objects.update_or_create(
                adventure=adventure,
                defaults={
                    "default_location": location_map.get(hero_setup_data.get("default_location")),
                    "require_race": hero_setup_data.get("require_race", True),
                    "default_race": race_map.get(hero_setup_data.get("default_race")),
                    "require_age": hero_setup_data.get("require_age", False),
                    "default_age": hero_setup_data.get("default_age"),
                    "require_body_power": hero_setup_data.get("require_body_power", True),
                    "default_body_power": hero_setup_data.get("default_body_power"),
                    "require_mind_power": hero_setup_data.get("require_mind_power", True),
                    "default_mind_power": hero_setup_data.get("default_mind_power"),
                    "require_will_power": hero_setup_data.get("require_will_power", True),
                    "default_will_power": hero_setup_data.get("default_will_power"),
                    "require_systems": hero_setup_data.get("require_systems", False),
                    "require_techniques": hero_setup_data.get("require_techniques", False),
                },
            )

        return Response(
            AdventureTemplateSerializer(adventure, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )
