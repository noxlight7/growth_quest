"""Persistent, bounded narrative consequence memory for story generation."""
from __future__ import annotations

import json
from collections.abc import Iterable

from django.db.models import Q

from ..models import (
    Adventure,
    AdventureHistory,
    Character,
    CharacterFaction,
    Faction,
    Location,
    NarrativeConsequence,
    NarrativeConsequenceCharacter,
    NarrativeConsequenceFaction,
    NarrativeConsequenceLocation,
)


MAX_CONTEXT_CONSEQUENCES = 12
MAX_CANDIDATE_CONSEQUENCES = 40
MAX_SUMMARY_CHARS = 520
MAX_ENTITY_TITLE_CHARS = 160
MAX_LINKS_PER_ENTITY_TYPE = 8
NARRATIVE_CONTEXT_TEXT = {
    "ru": (
        "Релевантная память о нравственных причинно-следственных связях. Используй её, чтобы "
        "сделать текущую сцену богаче и последовательнее. Пусть доброта, честность, верность, "
        "смелость и ответственность со временем открывают приятные возможности. Пусть жестокость, "
        "эксплуатация, предательство и эгоистичный вред создают значимые издержки и закрывают "
        "возможности через правдоподобную сюжетную причинность. Делай результат разнообразным, "
        "интересным и встроенным в вымышленный мир, а не механическим. Связанные сущности включены "
        "только на один уровень; не добавляй рекурсивно их другие воспоминания:\n"
    ),
    "en": (
        "Relevant moral cause-and-effect memory. Use it to make the current scene richer and "
        "more coherent. Let kindness, honesty, loyalty, courage, and responsibility open "
        "satisfying possibilities over time. Let cruelty, exploitation, betrayal, and selfish "
        "harm create meaningful costs and close possibilities through believable story causality. "
        "Keep the result varied, interesting, and integrated into the fiction rather than mechanical. "
        "Linked entities are included one hop deep; do not recursively expand their other memories:\n"
    ),
    "zh-CN": (
        "相关的道德因果记忆。用它让当前场景更丰富、更连贯。让善良、诚实、忠诚、勇敢和责任感"
        "随时间开启令人满意的可能性。让残酷、利用、背叛和自私伤害通过可信的剧情因果带来有意义"
        "的代价并关闭某些可能性。让结果多样、有趣，并融入虚构世界，而不是机械化呈现。关联实体"
        "只包含一层关系；不要递归展开它们的其他记忆：\n"
    ),
}
CERTAINTY_ORDER = {
    NarrativeConsequence.Certainty.INTENT: 0,
    NarrativeConsequence.Certainty.ATTEMPTED: 1,
    NarrativeConsequence.Certainty.ESTABLISHED: 2,
}


def _trim(value: object, limit: int) -> str:
    return str(value or "").strip()[:limit]


def _linked_ids(consequence: NarrativeConsequence) -> tuple[set[int], set[int], set[int]]:
    character_ids = {link.character_id for link in consequence.character_links.all()}
    location_ids = {link.location_id for link in consequence.location_links.all()}
    faction_ids = {link.faction_id for link in consequence.faction_links.all()}
    return character_ids, location_ids, faction_ids


def _serialize_consequence(consequence: NarrativeConsequence) -> dict:
    characters = [
        {"id": link.character_id, "title": _trim(link.character.title, MAX_ENTITY_TITLE_CHARS)}
        for link in consequence.character_links.all()[:MAX_LINKS_PER_ENTITY_TYPE]
    ]
    locations = [
        {"id": link.location_id, "title": _trim(link.location.title, MAX_ENTITY_TITLE_CHARS)}
        for link in consequence.location_links.all()[:MAX_LINKS_PER_ENTITY_TYPE]
    ]
    factions = [
        {"id": link.faction_id, "title": _trim(link.faction.title, MAX_ENTITY_TITLE_CHARS)}
        for link in consequence.faction_links.all()[:MAX_LINKS_PER_ENTITY_TYPE]
    ]
    return {
        "id": consequence.id,
        "title": _trim(consequence.title, 160),
        "summary": _trim(consequence.summary, MAX_SUMMARY_CHARS),
        "status": consequence.status,
        "certainty": consequence.certainty,
        "importance": consequence.importance,
        "characters": characters,
        "locations": locations,
        "factions": factions,
    }


def get_relevant_narrative_consequences(
    adventure: Adventure,
    *,
    current_location_id: int | None = None,
    character_ids: Iterable[int] = (),
    faction_ids: Iterable[int] = (),
    limit: int = MAX_CONTEXT_CONSEQUENCES,
    include_unestablished: bool = False,
) -> list[dict]:
    """Return a bounded set of active consequences with one-hop entity context."""
    if not adventure.narrative_consequences_enabled:
        return []

    relevant_characters = set(character_ids)
    relevant_factions = set(faction_ids)
    relevant_locations = {current_location_id} if current_location_id else set()
    active_consequences = NarrativeConsequence.objects.filter(
        adventure=adventure,
        status=NarrativeConsequence.Status.ACTIVE,
    )
    if not include_unestablished:
        active_consequences = active_consequences.filter(
            certainty=NarrativeConsequence.Certainty.ESTABLISHED,
        )
    candidate_ids = set(
        active_consequences.order_by("-importance", "-updated_at")
        .values_list("id", flat=True)[:MAX_CANDIDATE_CONSEQUENCES]
    )
    direct_filter = Q()
    has_direct_filter = False
    if relevant_characters:
        direct_filter |= Q(character_links__character_id__in=relevant_characters)
        has_direct_filter = True
    if relevant_locations:
        direct_filter |= Q(location_links__location_id__in=relevant_locations)
        has_direct_filter = True
    if relevant_factions:
        direct_filter |= Q(faction_links__faction_id__in=relevant_factions)
        has_direct_filter = True
    if has_direct_filter:
        candidate_ids.update(
            active_consequences.filter(direct_filter)
            .order_by("-importance", "-updated_at")
            .values_list("id", flat=True)
            .distinct()[:MAX_CANDIDATE_CONSEQUENCES]
        )

    candidates = list(
        active_consequences.filter(id__in=candidate_ids)
        .prefetch_related(
            "character_links__character",
            "location_links__location",
            "faction_links__faction",
        )
    )

    def rank(consequence: NarrativeConsequence) -> tuple[int, int, float]:
        linked_characters, linked_locations, linked_factions = _linked_ids(consequence)
        relevance = (
            len(linked_characters & relevant_characters) * 4
            + len(linked_locations & relevant_locations) * 5
            + len(linked_factions & relevant_factions) * 3
        )
        return relevance, consequence.importance, consequence.updated_at.timestamp()

    candidates.sort(key=rank, reverse=True)
    return [_serialize_consequence(consequence) for consequence in candidates[: max(0, limit)]]


def build_narrative_consequence_context(
    adventure: Adventure,
    *,
    current_location_id: int | None = None,
    character_ids: Iterable[int] = (),
    faction_ids: Iterable[int] = (),
    limit: int = MAX_CONTEXT_CONSEQUENCES,
    locale: str = "en",
) -> str:
    consequences = get_relevant_narrative_consequences(
        adventure,
        current_location_id=current_location_id,
        character_ids=character_ids,
        faction_ids=faction_ids,
        limit=limit,
    )
    if not consequences:
        return ""
    context_text = NARRATIVE_CONTEXT_TEXT.get(locale, NARRATIVE_CONTEXT_TEXT["en"])
    return f"{context_text}{json.dumps(consequences, ensure_ascii=False)}\n\n"


def get_current_entity_scope(adventure: Adventure) -> tuple[int | None, set[int], set[int]]:
    current_location_id = adventure.shared_location_id
    if current_location_id is None:
        primary_hero = adventure.primary_heroes.order_by("id").first() or adventure.primary_hero
        current_location_id = primary_hero.location_id if primary_hero else None
    character_ids = set(
        Character.objects.filter(
            adventure=adventure,
            in_party=True,
            story_status=Character.StoryStatus.ACTIVE,
        ).values_list("id", flat=True)
    )
    if current_location_id:
        character_ids.update(
            Character.objects.filter(
                adventure=adventure,
                location_id=current_location_id,
            ).values_list("id", flat=True)
        )
    faction_ids = set(
        CharacterFaction.objects.filter(character_id__in=character_ids).values_list(
            "faction_id",
            flat=True,
        )
    )
    return current_location_id, character_ids, faction_ids


def _valid_ids(queryset, raw_ids: object) -> set[int]:
    if not isinstance(raw_ids, list):
        return set()
    ids = []
    for value in raw_ids[:MAX_LINKS_PER_ENTITY_TYPE]:
        try:
            ids.append(int(value))
        except (TypeError, ValueError):
            continue
    return set(queryset.filter(id__in=ids).values_list("id", flat=True))


def _replace_links(
    consequence: NarrativeConsequence,
    *,
    character_ids: set[int] | None = None,
    location_ids: set[int] | None = None,
    faction_ids: set[int] | None = None,
) -> None:
    if character_ids is not None:
        consequence.character_links.all().delete()
        NarrativeConsequenceCharacter.objects.bulk_create(
            [
                NarrativeConsequenceCharacter(consequence=consequence, character_id=character_id)
                for character_id in character_ids
            ]
        )
    if location_ids is not None:
        consequence.location_links.all().delete()
        NarrativeConsequenceLocation.objects.bulk_create(
            [
                NarrativeConsequenceLocation(consequence=consequence, location_id=location_id)
                for location_id in location_ids
            ]
        )
    if faction_ids is not None:
        consequence.faction_links.all().delete()
        NarrativeConsequenceFaction.objects.bulk_create(
            [
                NarrativeConsequenceFaction(consequence=consequence, faction_id=faction_id)
                for faction_id in faction_ids
            ]
        )


def snapshot_narrative_consequence(consequence: NarrativeConsequence) -> dict:
    return {
        "id": consequence.id,
        "title": consequence.title,
        "summary": consequence.summary,
        "status": consequence.status,
        "certainty": consequence.certainty,
        "importance": consequence.importance,
        "characters": list(consequence.character_links.values_list("character_id", flat=True)),
        "locations": list(consequence.location_links.values_list("location_id", flat=True)),
        "factions": list(consequence.faction_links.values_list("faction_id", flat=True)),
    }


def restore_narrative_consequence_snapshot(adventure: Adventure, snapshot: dict) -> None:
    try:
        consequence_id = int(snapshot.get("id"))
    except (TypeError, ValueError):
        return
    consequence = NarrativeConsequence.objects.filter(
        adventure=adventure,
        id=consequence_id,
    ).first()
    if consequence is None:
        return
    status = snapshot.get("status")
    certainty = snapshot.get("certainty")
    try:
        importance = max(1, min(5, int(snapshot.get("importance", 1))))
    except (TypeError, ValueError):
        importance = 1
    if status not in NarrativeConsequence.Status.values:
        status = NarrativeConsequence.Status.ACTIVE
    if certainty not in NarrativeConsequence.Certainty.values:
        certainty = NarrativeConsequence.Certainty.ESTABLISHED
    consequence.title = _trim(snapshot.get("title"), 200)
    consequence.summary = _trim(snapshot.get("summary"), 1200)
    consequence.status = status
    consequence.certainty = certainty
    consequence.importance = importance
    consequence.save(
        update_fields=["title", "summary", "status", "certainty", "importance", "updated_at"]
    )
    characters = Character.objects.filter(adventure=adventure)
    locations = Location.objects.filter(adventure=adventure)
    factions = Faction.objects.filter(adventure=adventure)
    _replace_links(
        consequence,
        character_ids=_valid_ids(characters, snapshot.get("characters")),
        location_ids=_valid_ids(locations, snapshot.get("locations")),
        faction_ids=_valid_ids(factions, snapshot.get("factions")),
    )


def apply_narrative_consequence_updates(
    adventure: Adventure,
    updates: object,
    *,
    source_history_entry: AdventureHistory | None = None,
    default_certainty: str = NarrativeConsequence.Certainty.ESTABLISHED,
    preserve_established: bool = True,
) -> list[NarrativeConsequence]:
    """Apply validated analyzer or compaction updates without trusting model-provided IDs."""
    if not adventure.narrative_consequences_enabled or not isinstance(updates, list):
        return []

    characters = Character.objects.filter(adventure=adventure)
    locations = Location.objects.filter(adventure=adventure)
    factions = Faction.objects.filter(adventure=adventure)
    touched: list[NarrativeConsequence] = []

    for item in updates[:12]:
        if not isinstance(item, dict):
            continue
        consequence = None
        try:
            consequence_id = int(item.get("id")) if item.get("id") is not None else None
        except (TypeError, ValueError):
            consequence_id = None
        if consequence_id:
            consequence = NarrativeConsequence.objects.filter(
                adventure=adventure,
                id=consequence_id,
            ).first()

        title = _trim(item.get("title"), 200)
        summary = _trim(item.get("summary"), 1200)
        status = item.get("status")
        if status not in NarrativeConsequence.Status.values:
            status = NarrativeConsequence.Status.ACTIVE
        certainty = item.get("certainty", default_certainty)
        if certainty not in NarrativeConsequence.Certainty.values:
            certainty = default_certainty
        if certainty not in NarrativeConsequence.Certainty.values:
            certainty = NarrativeConsequence.Certainty.ESTABLISHED
        if (
            consequence is not None
            and preserve_established
            and consequence.certainty == NarrativeConsequence.Certainty.ESTABLISHED
            and certainty != NarrativeConsequence.Certainty.ESTABLISHED
        ):
            consequence = None
        try:
            importance = max(1, min(5, int(item.get("importance", 1))))
        except (TypeError, ValueError):
            importance = 1

        if consequence is None:
            if not title or not summary:
                continue
            matching_consequences = NarrativeConsequence.objects.filter(
                adventure=adventure,
                title=title,
            )
            if preserve_established and certainty != NarrativeConsequence.Certainty.ESTABLISHED:
                matching_consequences = matching_consequences.exclude(
                    certainty=NarrativeConsequence.Certainty.ESTABLISHED,
                )
            consequence = matching_consequences.first()
            if consequence is None:
                consequence = NarrativeConsequence.objects.create(
                    adventure=adventure,
                    source_history_entry=source_history_entry,
                    title=title,
                    summary=summary,
                    status=status,
                    certainty=certainty,
                    importance=importance,
                )
        if consequence.pk:
            update_fields = []
            if title:
                consequence.title = title
                update_fields.append("title")
            if summary:
                consequence.summary = summary
                update_fields.append("summary")
            consequence.status = status
            consequence.importance = importance
            if CERTAINTY_ORDER[certainty] >= CERTAINTY_ORDER[consequence.certainty]:
                consequence.certainty = certainty
                update_fields.append("certainty")
            update_fields.extend(["status", "importance", "updated_at"])
            consequence.save(update_fields=update_fields)

        _replace_links(
            consequence,
            character_ids=_valid_ids(characters, item.get("characters"))
            if "characters" in item
            else None,
            location_ids=_valid_ids(locations, item.get("locations"))
            if "locations" in item
            else None,
            faction_ids=_valid_ids(factions, item.get("factions"))
            if "factions" in item
            else None,
        )
        touched.append(consequence)

    return touched
