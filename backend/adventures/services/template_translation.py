"""LLM-backed translation and cloning for adventure templates."""
from __future__ import annotations

from dataclasses import dataclass
import json
import os
from typing import Any

from django.db import transaction

from backend.llm import LLMClient

from ..models import (
    Adventure,
    AdventureEvent,
    AdventureHeroSetup,
    Character,
    CharacterFaction,
    CharacterRelationship,
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


LOCALE_NAMES = {
    Adventure.StoryLocale.RU: "Russian",
    Adventure.StoryLocale.EN: "English",
    Adventure.StoryLocale.ZH_CN: "Simplified Chinese",
}


class TemplateTranslationError(ValueError):
    """Raised when a model response cannot be used for a complete translation."""


@dataclass(frozen=True)
class TranslationItem:
    key: str
    text: str


@dataclass(frozen=True)
class TemplateTranslationResult:
    template: Adventure
    translated_fields: int
    batches: int


@dataclass
class TemplateSnapshot:
    template: Adventure
    hero_setup: AdventureHeroSetup | None
    locations: list[Location]
    races: list[Race]
    systems: list[SkillSystem]
    techniques: list[Technique]
    factions: list[Faction]
    other_info: list[OtherInfo]
    events: list[AdventureEvent]
    objectives: list[LearningObjective]
    reflection_prompts: list[ReflectionPrompt]
    interventions: list[PedagogicalIntervention]
    characters: list[Character]
    character_systems: list[CharacterSystem]
    character_techniques: list[CharacterTechnique]
    character_factions: list[CharacterFaction]
    relationships: list[CharacterRelationship]
    primary_hero_ids: list[int]


TRANSLATABLE_MODEL_FIELDS = {
    "adventure": ("title", "description", "intro", "spec_instructions"),
    "location": ("title", "description"),
    "race": ("title", "description"),
    "system": ("title", "description", "formula_hint"),
    "technique": ("title", "description"),
    "faction": ("title", "description"),
    "other_info": ("category", "title", "description"),
    "event": ("title", "trigger_hint", "state"),
    "objective": ("title", "description"),
    "reflection_prompt": ("question",),
    "character": ("title", "description"),
    "character_system": ("notes",),
    "character_technique": ("notes",),
    "relationship": ("description",),
}


def _field_key(kind: str, object_id: int, field: str) -> str:
    return f"{kind}:{object_id}:{field}"


def _snapshot_template(template: Adventure) -> TemplateSnapshot:
    primary_hero_ids = list(template.primary_heroes.values_list("id", flat=True))
    if not primary_hero_ids and template.primary_hero_id:
        primary_hero_ids = [template.primary_hero_id]
    return TemplateSnapshot(
        template=template,
        hero_setup=AdventureHeroSetup.objects.filter(adventure=template).first(),
        locations=list(Location.objects.filter(adventure=template).order_by("id")),
        races=list(Race.objects.filter(adventure=template).order_by("id")),
        systems=list(SkillSystem.objects.filter(adventure=template).order_by("id")),
        techniques=list(Technique.objects.filter(system__adventure=template).order_by("id")),
        factions=list(Faction.objects.filter(adventure=template).order_by("id")),
        other_info=list(OtherInfo.objects.filter(adventure=template).order_by("id")),
        events=list(AdventureEvent.objects.filter(adventure=template).order_by("id")),
        objectives=list(LearningObjective.objects.filter(adventure=template).order_by("id")),
        reflection_prompts=list(ReflectionPrompt.objects.filter(adventure=template).order_by("id")),
        interventions=list(
            PedagogicalIntervention.objects.filter(adventure=template).order_by("id")
        ),
        characters=list(Character.objects.filter(adventure=template).order_by("id")),
        character_systems=list(
            CharacterSystem.objects.filter(character__adventure=template).order_by("id")
        ),
        character_techniques=list(
            CharacterTechnique.objects.filter(character__adventure=template).order_by("id")
        ),
        character_factions=list(
            CharacterFaction.objects.filter(character__adventure=template).order_by("id")
        ),
        relationships=list(
            CharacterRelationship.objects.filter(from_character__adventure=template).order_by("id")
        ),
        primary_hero_ids=primary_hero_ids,
    )


def _append_model_fields(
    items: list[TranslationItem],
    kind: str,
    instances: list[Any],
) -> None:
    for instance in instances:
        for field in TRANSLATABLE_MODEL_FIELDS[kind]:
            text = getattr(instance, field)
            if isinstance(text, str) and text.strip():
                items.append(TranslationItem(_field_key(kind, instance.id, field), text))


def _collect_payload_strings(value: Any, prefix: str, items: list[TranslationItem]) -> None:
    if isinstance(value, str):
        if value.strip():
            items.append(TranslationItem(prefix, value))
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _collect_payload_strings(item, f"{prefix}[{index}]", items)
        return
    if isinstance(value, dict):
        for key, item in value.items():
            _collect_payload_strings(item, f"{prefix}.{key}", items)


def _collect_translation_items(snapshot: TemplateSnapshot) -> list[TranslationItem]:
    items: list[TranslationItem] = []
    _append_model_fields(items, "adventure", [snapshot.template])
    _append_model_fields(items, "location", snapshot.locations)
    _append_model_fields(items, "race", snapshot.races)
    _append_model_fields(items, "system", snapshot.systems)
    _append_model_fields(items, "technique", snapshot.techniques)
    _append_model_fields(items, "faction", snapshot.factions)
    _append_model_fields(items, "other_info", snapshot.other_info)
    _append_model_fields(items, "event", snapshot.events)
    _append_model_fields(items, "objective", snapshot.objectives)
    _append_model_fields(items, "reflection_prompt", snapshot.reflection_prompts)
    _append_model_fields(items, "character", snapshot.characters)
    _append_model_fields(items, "character_system", snapshot.character_systems)
    _append_model_fields(items, "character_technique", snapshot.character_techniques)
    _append_model_fields(items, "relationship", snapshot.relationships)
    for intervention in snapshot.interventions:
        _collect_payload_strings(
            intervention.payload,
            f"intervention:{intervention.id}:payload",
            items,
        )
    return items


def _iter_batches(items: list[TranslationItem]) -> list[list[TranslationItem]]:
    max_items = max(1, int(os.getenv("TEMPLATE_TRANSLATION_BATCH_MAX_ITEMS", "24")))
    max_chars = max(500, int(os.getenv("TEMPLATE_TRANSLATION_BATCH_MAX_CHARS", "7000")))
    batches: list[list[TranslationItem]] = []
    batch: list[TranslationItem] = []
    batch_chars = 0
    for item in items:
        item_chars = len(item.key) + len(item.text)
        if batch and (len(batch) >= max_items or batch_chars + item_chars > max_chars):
            batches.append(batch)
            batch = []
            batch_chars = 0
        batch.append(item)
        batch_chars += item_chars
    if batch:
        batches.append(batch)
    return batches


def _extract_json_object(raw_text: str) -> dict:
    cleaned = raw_text.strip().replace("```json", "").replace("```", "").strip()
    try:
        payload = json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start == -1 or end <= start:
            raise TemplateTranslationError("The translation model did not return valid JSON.")
        try:
            payload = json.loads(cleaned[start : end + 1])
        except json.JSONDecodeError as exc:
            raise TemplateTranslationError("The translation model did not return valid JSON.") from exc
    if not isinstance(payload, dict):
        raise TemplateTranslationError("The translation model returned an invalid JSON object.")
    return payload


def _build_translation_prompt(
    items: list[TranslationItem],
    *,
    source_locale: str,
    target_locale: str,
) -> str:
    source_name = LOCALE_NAMES[source_locale]
    target_name = LOCALE_NAMES[target_locale]
    source_items = [{"key": item.key, "text": item.text} for item in items]
    return (
        f"Translate the supplied adventure-template text from {source_name} to {target_name}.\n"
        "Return only valid JSON without markdown or commentary.\n"
        'Schema: {"translations":[{"key":"unchanged input key","text":"translated text"}]}\n'
        "Rules:\n"
        "- Return exactly one translation for every input key and preserve each key verbatim.\n"
        "- Translate only text values. Preserve placeholders such as <main_hero>, formatting, "
        "numbers, formulas, and inline code.\n"
        "- Keep proper names consistent across all entries in this batch.\n"
        "- Preserve the meaning and tone. Do not summarize, expand, censor, or add explanations.\n"
        "- Write every translated text value in the requested target language.\n\n"
        f"Input: {json.dumps(source_items, ensure_ascii=False)}"
    )


def _translate_batch(
    client: LLMClient,
    items: list[TranslationItem],
    *,
    source_locale: str,
    target_locale: str,
) -> dict[str, str]:
    response = client.generate(
        prompt=_build_translation_prompt(
            items,
            source_locale=source_locale,
            target_locale=target_locale,
        ),
        system=(
            "You are a precise localization engine for narrative-game templates. "
            "Translate all requested fields and obey the JSON contract exactly."
        ),
        temperature=0.0,
        max_tokens=4000,
    )
    payload = _extract_json_object(response.text)
    raw_translations = payload.get("translations")
    if not isinstance(raw_translations, list):
        raise TemplateTranslationError("The translation model omitted the translations list.")
    translations: dict[str, str] = {}
    for entry in raw_translations:
        if not isinstance(entry, dict):
            continue
        key = entry.get("key")
        text = entry.get("text")
        if isinstance(key, str) and isinstance(text, str) and key not in translations:
            translations[key] = text
    expected_keys = {item.key for item in items}
    if set(translations) != expected_keys:
        raise TemplateTranslationError("The translation model returned an incomplete field set.")
    return translations


def _translate_items(
    client: LLMClient,
    items: list[TranslationItem],
    *,
    source_locale: str,
    target_locale: str,
) -> tuple[dict[str, str], int]:
    translations: dict[str, str] = {}
    batches = _iter_batches(items)
    for batch in batches:
        translations.update(
            _translate_batch(
                client,
                batch,
                source_locale=source_locale,
                target_locale=target_locale,
            )
        )
    return translations, len(batches)


def _translated_field(
    translations: dict[str, str],
    kind: str,
    instance: Any,
    field: str,
) -> str:
    value = getattr(instance, field)
    return translations.get(_field_key(kind, instance.id, field), value)


def _translated_payload(value: Any, prefix: str, translations: dict[str, str]) -> Any:
    if isinstance(value, str):
        return translations.get(prefix, value)
    if isinstance(value, list):
        return [
            _translated_payload(item, f"{prefix}[{index}]", translations)
            for index, item in enumerate(value)
        ]
    if isinstance(value, dict):
        return {
            key: _translated_payload(item, f"{prefix}.{key}", translations)
            for key, item in value.items()
        }
    return value


@transaction.atomic
def _clone_template(
    snapshot: TemplateSnapshot,
    translations: dict[str, str],
    *,
    author_user,
    target_locale: str,
) -> Adventure:
    source = snapshot.template
    copied = Adventure.objects.create(
        author_user=author_user,
        player_user=None,
        template_adventure=None,
        is_template=True,
        title=_translated_field(translations, "adventure", source, "title"),
        description=_translated_field(translations, "adventure", source, "description"),
        intro=_translated_field(translations, "adventure", source, "intro"),
        spec_instructions=_translated_field(translations, "adventure", source, "spec_instructions"),
        story_locale=target_locale,
        facilitator_enabled=source.facilitator_enabled,
        story_simple_language=source.story_simple_language,
        story_reduced_text_length=source.story_reduced_text_length,
        growth_analysis_enabled=source.growth_analysis_enabled,
        narrative_consequences_enabled=source.narrative_consequences_enabled,
        max_players=source.max_players,
    )

    location_map = {}
    for item in snapshot.locations:
        location_map[item.id] = Location.objects.create(
            adventure=copied,
            title=_translated_field(translations, "location", item, "title"),
            description=_translated_field(translations, "location", item, "description"),
            x=item.x,
            y=item.y,
            width=item.width,
            height=item.height,
            tags=list(item.tags),
        )

    race_map = {}
    for item in snapshot.races:
        race_map[item.id] = Race.objects.create(
            adventure=copied,
            title=_translated_field(translations, "race", item, "title"),
            description=_translated_field(translations, "race", item, "description"),
            life_span=item.life_span,
            tags=list(item.tags),
        )

    system_map = {}
    for item in snapshot.systems:
        system_map[item.id] = SkillSystem.objects.create(
            adventure=copied,
            title=_translated_field(translations, "system", item, "title"),
            description=_translated_field(translations, "system", item, "description"),
            tags=list(item.tags),
            w_body=item.w_body,
            w_mind=item.w_mind,
            w_will=item.w_will,
            formula_hint=_translated_field(translations, "system", item, "formula_hint"),
        )

    technique_map = {}
    for item in snapshot.techniques:
        system = system_map.get(item.system_id)
        if system:
            technique_map[item.id] = Technique.objects.create(
                system=system,
                title=_translated_field(translations, "technique", item, "title"),
                description=_translated_field(translations, "technique", item, "description"),
                tags=list(item.tags),
                difficulty=item.difficulty,
                tier=item.tier,
                required_system_level=item.required_system_level,
            )

    faction_map = {}
    for item in snapshot.factions:
        faction_map[item.id] = Faction.objects.create(
            adventure=copied,
            title=_translated_field(translations, "faction", item, "title"),
            description=_translated_field(translations, "faction", item, "description"),
            tags=list(item.tags),
        )

    for item in snapshot.other_info:
        OtherInfo.objects.create(
            adventure=copied,
            category=_translated_field(translations, "other_info", item, "category"),
            title=_translated_field(translations, "other_info", item, "title"),
            description=_translated_field(translations, "other_info", item, "description"),
            tags=list(item.tags),
        )

    for item in snapshot.events:
        AdventureEvent.objects.create(
            adventure=copied,
            location=location_map.get(item.location_id),
            status=item.status,
            title=_translated_field(translations, "event", item, "title"),
            trigger_hint=_translated_field(translations, "event", item, "trigger_hint"),
            state=_translated_field(translations, "event", item, "state"),
        )

    objective_map = {}
    for item in snapshot.objectives:
        objective_map[item.id] = LearningObjective.objects.create(
            adventure=copied,
            code=item.code,
            title=_translated_field(translations, "objective", item, "title"),
            description=_translated_field(translations, "objective", item, "description"),
            competency=item.competency,
            weight=item.weight,
            is_active=item.is_active,
        )

    for item in snapshot.reflection_prompts:
        objective = objective_map.get(item.objective_id)
        if objective:
            ReflectionPrompt.objects.create(
                adventure=copied,
                objective=objective,
                trigger_kind=item.trigger_kind,
                question=_translated_field(translations, "reflection_prompt", item, "question"),
                is_active=item.is_active,
            )

    for item in snapshot.interventions:
        objective = objective_map.get(item.objective_id)
        if objective:
            PedagogicalIntervention.objects.create(
                adventure=copied,
                objective=objective,
                kind=item.kind,
                payload=_translated_payload(
                    item.payload,
                    f"intervention:{item.id}:payload",
                    translations,
                ),
                is_active=item.is_active,
            )

    character_map = {}
    for item in snapshot.characters:
        character_map[item.id] = Character.objects.create(
            adventure=copied,
            race=race_map.get(item.race_id),
            location=location_map.get(item.location_id),
            is_player=item.is_player,
            in_party=item.in_party,
            story_status=item.story_status,
            title=_translated_field(translations, "character", item, "title"),
            age=item.age,
            body_power=item.body_power,
            body_power_progress=item.body_power_progress,
            mind_power=item.mind_power,
            mind_power_progress=item.mind_power_progress,
            will_power=item.will_power,
            will_power_progress=item.will_power_progress,
            description=_translated_field(translations, "character", item, "description"),
            tags=list(item.tags),
        )

    for item in snapshot.character_systems:
        character = character_map.get(item.character_id)
        system = system_map.get(item.system_id)
        if character and system:
            CharacterSystem.objects.create(
                character=character,
                system=system,
                level=item.level,
                progress_percent=item.progress_percent,
                notes=_translated_field(translations, "character_system", item, "notes"),
            )

    for item in snapshot.character_techniques:
        character = character_map.get(item.character_id)
        technique = technique_map.get(item.technique_id)
        if character and technique:
            CharacterTechnique.objects.create(
                character=character,
                technique=technique,
                notes=_translated_field(translations, "character_technique", item, "notes"),
            )

    for item in snapshot.character_factions:
        character = character_map.get(item.character_id)
        faction = faction_map.get(item.faction_id)
        if character and faction:
            CharacterFaction.objects.create(character=character, faction=faction)

    for item in snapshot.relationships:
        from_character = character_map.get(item.from_character_id)
        to_character = character_map.get(item.to_character_id)
        if from_character and to_character:
            CharacterRelationship.objects.create(
                from_character=from_character,
                to_character=to_character,
                kind=item.kind,
                description=_translated_field(translations, "relationship", item, "description"),
            )

    copied.shared_location = location_map.get(source.shared_location_id)
    copied.primary_hero = character_map.get(source.primary_hero_id)
    copied.save(update_fields=["shared_location", "primary_hero"])
    copied.primary_heroes.set(
        [character_map[hero_id] for hero_id in snapshot.primary_hero_ids if hero_id in character_map]
    )

    source_setup = snapshot.hero_setup
    AdventureHeroSetup.objects.create(
        adventure=copied,
        default_location=location_map.get(source_setup.default_location_id) if source_setup else None,
        require_race=source_setup.require_race if source_setup else True,
        default_race=race_map.get(source_setup.default_race_id) if source_setup else None,
        require_age=source_setup.require_age if source_setup else False,
        default_age=source_setup.default_age if source_setup else None,
        require_body_power=source_setup.require_body_power if source_setup else True,
        default_body_power=source_setup.default_body_power if source_setup else None,
        require_mind_power=source_setup.require_mind_power if source_setup else True,
        default_mind_power=source_setup.default_mind_power if source_setup else None,
        require_will_power=source_setup.require_will_power if source_setup else True,
        default_will_power=source_setup.default_will_power if source_setup else None,
        require_systems=source_setup.require_systems if source_setup else False,
        require_techniques=source_setup.require_techniques if source_setup else False,
    )
    return copied


def clone_translated_template(
    template: Adventure,
    *,
    target_locale: str,
    client: LLMClient,
    author_user: Any,
) -> TemplateTranslationResult:
    if not template.is_template:
        raise TemplateTranslationError("Only adventure templates can be translated.")
    if target_locale not in Adventure.StoryLocale.values:
        raise TemplateTranslationError("Unsupported target locale.")
    if target_locale == template.story_locale:
        raise TemplateTranslationError("The target locale must differ from the source locale.")

    snapshot = _snapshot_template(template)
    items = _collect_translation_items(snapshot)
    translations, batch_count = _translate_items(
        client,
        items,
        source_locale=template.story_locale,
        target_locale=target_locale,
    )
    copied = _clone_template(
        snapshot,
        translations,
        author_user=author_user,
        target_locale=target_locale,
    )
    return TemplateTranslationResult(
        template=copied,
        translated_fields=len(items),
        batches=batch_count,
    )
