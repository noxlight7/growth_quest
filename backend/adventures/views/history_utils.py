"""History preparation and card update helpers for AI prompts."""
from __future__ import annotations

import json

from backend.llm import LLMClient

from ..models import (
    Adventure,
    AdventureEvent,
    AdventureHistory,
    AdventureMemory,
    Character,
    CharacterRelationship,
    CharacterSystem,
    CharacterTechnique,
    ConsequenceMarker,
    LearningObjective,
    RepairOpportunity,
)
from ..services.narrative_consequences import apply_narrative_consequence_updates
from .prompts import _build_card_update_prompt, _get_history_limits, _get_update_token_limits


def _extract_json_payload(text: str) -> dict | None:
    cleaned = text.strip()
    if not cleaned:
        return None
    cleaned = cleaned.replace("```json", "").replace("```", "").strip()
    try:
        payload = json.loads(cleaned)
        return payload if isinstance(payload, dict) else None
    except json.JSONDecodeError:
        pass
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    snippet = cleaned[start : end + 1]
    try:
        payload = json.loads(snippet)
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def _as_int(value, default: int | None = None) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _clean_tags(value) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item).strip()][:12]


def _apply_card_updates(
    adventure: Adventure,
    payload: dict,
    *,
    source_history_entry: AdventureHistory | None = None,
) -> None:
    active_growth_competencies = (
        set(
            LearningObjective.objects.filter(
                adventure=adventure,
                is_active=True,
            ).values_list("competency", flat=True)
        )
        if adventure.growth_analysis_enabled
        else set()
    )
    events_updates = payload.get("events", [])
    if isinstance(events_updates, list) and events_updates:
        for entry in events_updates:
            if not isinstance(entry, dict):
                continue
            event_id = entry.get("id")
            if not event_id:
                continue
            event = AdventureEvent.objects.filter(adventure=adventure, id=event_id).first()
            if event is None:
                continue
            status = entry.get("status")
            state = entry.get("state")
            update_fields = []
            if status in AdventureEvent.Status.values:
                event.status = status
                update_fields.append("status")
            if isinstance(state, str):
                event.state = state
                update_fields.append("state")
            if update_fields:
                event.save(update_fields=update_fields)

    characters_updates = payload.get("characters", [])
    if isinstance(characters_updates, list) and characters_updates:
        for entry in characters_updates:
            if not isinstance(entry, dict):
                continue
            character_id = entry.get("id")
            if not character_id:
                continue
            character = Character.objects.filter(adventure=adventure, id=character_id).first()
            if character is None:
                continue
            update_fields = []
            if "description" in entry and isinstance(entry.get("description"), str):
                character.description = entry.get("description")
                update_fields.append("description")
            story_status = entry.get("story_status")
            if story_status in Character.StoryStatus.values:
                character.story_status = story_status
                update_fields.append("story_status")
                if story_status != Character.StoryStatus.ACTIVE and character.in_party:
                    character.in_party = False
                    update_fields.append("in_party")
            for field in (
                "body_power",
                "mind_power",
                "will_power",
                "body_power_progress",
                "mind_power_progress",
                "will_power_progress",
            ):
                if field not in entry or entry.get(field) is None:
                    continue
                value = int(entry.get(field))
                if field.endswith("_progress"):
                    value = max(0, min(100, value))
                setattr(character, field, value)
                update_fields.append(field)
            if update_fields:
                character.save(update_fields=update_fields)

    system_updates = payload.get("character_systems", [])
    if isinstance(system_updates, list) and system_updates:
        for entry in system_updates:
            if not isinstance(entry, dict):
                continue
            record_id = entry.get("id")
            if not record_id:
                continue
            record = CharacterSystem.objects.filter(
                character__adventure=adventure, id=record_id
            ).first()
            if record is None:
                continue
            update_fields = []
            current_level = record.level
            current_progress = record.progress_percent
            new_level = entry.get("level")
            new_progress = entry.get("progress_percent")
            if new_level is not None:
                new_level = int(new_level)
                if new_level >= current_level:
                    record.level = new_level
                    update_fields.append("level")
            if new_progress is not None:
                new_progress = int(new_progress)
                if new_level is not None and new_level > current_level:
                    record.progress_percent = new_progress
                    update_fields.append("progress_percent")
                elif new_progress >= current_progress:
                    record.progress_percent = new_progress
                    update_fields.append("progress_percent")
            if "notes" in entry and isinstance(entry.get("notes"), str):
                record.notes = entry.get("notes")
                update_fields.append("notes")
            if update_fields:
                record.save(update_fields=update_fields)

    technique_updates = payload.get("character_techniques", [])
    if isinstance(technique_updates, list) and technique_updates:
        for entry in technique_updates:
            if not isinstance(entry, dict):
                continue
            record_id = entry.get("id")
            if not record_id:
                continue
            record = CharacterTechnique.objects.filter(
                character__adventure=adventure, id=record_id
            ).first()
            if record is None:
                continue
            if "notes" in entry and isinstance(entry.get("notes"), str):
                record.notes = entry.get("notes")
                record.save(update_fields=["notes"])

    memory_updates = payload.get("memories", [])
    if isinstance(memory_updates, list) and memory_updates:
        for entry in memory_updates:
            if not isinstance(entry, dict):
                continue
            memory_id = entry.get("id")
            memory = None
            if memory_id:
                memory = AdventureMemory.objects.filter(
                    adventure=adventure,
                    id=memory_id,
                ).first()
            kind = entry.get("kind")
            if kind not in AdventureMemory.Kind.values:
                kind = AdventureMemory.Kind.FACT
            title = entry.get("title")
            content = entry.get("content")
            importance = _as_int(entry.get("importance"), 0)
            tags = _clean_tags(entry.get("tags"))
            if memory is None:
                if not isinstance(content, str) or not content.strip():
                    continue
                AdventureMemory.objects.create(
                    adventure=adventure,
                    kind=kind,
                    title=title if isinstance(title, str) else "",
                    content=content,
                    importance=importance or 0,
                    tags=tags,
                )
                continue
            update_fields = []
            if kind:
                memory.kind = kind
                update_fields.append("kind")
            if isinstance(title, str):
                memory.title = title
                update_fields.append("title")
            if isinstance(content, str):
                memory.content = content
                update_fields.append("content")
            if importance is not None:
                memory.importance = importance
                update_fields.append("importance")
            if "tags" in entry:
                memory.tags = tags
                update_fields.append("tags")
            if update_fields:
                memory.save(update_fields=update_fields)

    relationship_updates = payload.get("relationships", [])
    if isinstance(relationship_updates, list) and relationship_updates:
        for entry in relationship_updates:
            if not isinstance(entry, dict):
                continue
            relationship_id = entry.get("id")
            relationship = None
            if relationship_id:
                relationship = CharacterRelationship.objects.filter(
                    from_character__adventure=adventure,
                    id=relationship_id,
                ).first()
            from_character_id = _as_int(entry.get("from_character"))
            to_character_id = _as_int(entry.get("to_character"))
            kind = str(entry.get("kind") or "").strip()
            description = entry.get("description")
            if relationship is None:
                if not from_character_id or not to_character_id or not kind:
                    continue
                if from_character_id == to_character_id:
                    continue
                character_ids = set(
                    Character.objects.filter(
                        adventure=adventure,
                        id__in=[from_character_id, to_character_id],
                    ).values_list("id", flat=True)
                )
                if {from_character_id, to_character_id} != character_ids:
                    continue
                CharacterRelationship.objects.update_or_create(
                    from_character_id=from_character_id,
                    to_character_id=to_character_id,
                    kind=kind,
                    defaults={
                        "description": description if isinstance(description, str) else "",
                    },
                )
                continue
            update_fields = []
            if kind:
                relationship.kind = kind
                update_fields.append("kind")
            if isinstance(description, str):
                relationship.description = description
                update_fields.append("description")
            if update_fields:
                relationship.save(update_fields=update_fields)

    repair_updates = payload.get("repair_opportunities", []) if active_growth_competencies else []
    if isinstance(repair_updates, list) and repair_updates:
        for entry in repair_updates:
            if not isinstance(entry, dict):
                continue
            repair_id = entry.get("id")
            repair = None
            if repair_id:
                repair = RepairOpportunity.objects.filter(
                    adventure=adventure,
                    id=repair_id,
                ).first()
            competency = entry.get("competency")
            if competency not in active_growth_competencies:
                continue
            status = entry.get("status")
            title = entry.get("title")
            description = entry.get("description")
            suggested_action = entry.get("suggested_action")
            if repair is None:
                if not isinstance(title, str) or not title.strip():
                    continue
                RepairOpportunity.objects.create(
                    adventure=adventure,
                    source_history_entry=source_history_entry,
                    competency=competency,
                    status=status
                    if status in RepairOpportunity.Status.values
                    else RepairOpportunity.Status.OPEN,
                    title=title,
                    description=description if isinstance(description, str) else "",
                    suggested_action=suggested_action if isinstance(suggested_action, str) else "",
                )
                continue
            update_fields = []
            if competency:
                repair.competency = competency
                update_fields.append("competency")
            if status in RepairOpportunity.Status.values:
                repair.status = status
                update_fields.append("status")
            if isinstance(title, str):
                repair.title = title
                update_fields.append("title")
            if isinstance(description, str):
                repair.description = description
                update_fields.append("description")
            if isinstance(suggested_action, str):
                repair.suggested_action = suggested_action
                update_fields.append("suggested_action")
            if update_fields:
                repair.save(update_fields=update_fields)

    consequence_updates = payload.get("consequence_markers", []) if active_growth_competencies else []
    if isinstance(consequence_updates, list) and consequence_updates:
        for entry in consequence_updates:
            if not isinstance(entry, dict):
                continue
            kind = entry.get("kind")
            title = entry.get("title")
            if kind not in ConsequenceMarker.Kind.values:
                continue
            if not isinstance(title, str) or not title.strip():
                continue
            competency = entry.get("competency")
            if competency not in active_growth_competencies:
                continue
            ConsequenceMarker.objects.create(
                adventure=adventure,
                history_entry=source_history_entry,
                competency=competency,
                kind=kind,
                title=title,
                description=entry.get("description")
                if isinstance(entry.get("description"), str)
                else "",
                weight=_as_int(entry.get("weight"), 0) or 0,
                tags=_clean_tags(entry.get("tags")),
            )

    apply_narrative_consequence_updates(
        adventure,
        payload.get("narrative_consequences", []),
        source_history_entry=source_history_entry,
    )


def _prepare_history_for_prompt(adventure: Adventure, client: LLMClient) -> list[AdventureHistory]:
    history_entries = list(AdventureHistory.objects.filter(adventure=adventure).order_by("id"))
    max_posts, tail_posts = _get_history_limits()
    if len(history_entries) <= max_posts:
        return history_entries
    if tail_posts == 0:
        return history_entries[-max_posts:]
    visible_entries = history_entries
    if adventure.rollback_min_history_id:
        visible_entries = [
            entry for entry in history_entries if entry.id >= adventure.rollback_min_history_id
        ]
        if len(visible_entries) <= max_posts:
            return visible_entries
    update_max_tokens, strict_max_tokens = _get_update_token_limits()
    while len(visible_entries) > max_posts:
        if len(visible_entries) <= tail_posts:
            return visible_entries
        entries_to_compact = visible_entries[:tail_posts]
        update_prompt = _build_card_update_prompt(adventure, entries_to_compact)
        response = client.generate(prompt=update_prompt, max_tokens=update_max_tokens)
        payload = _extract_json_payload(response.text)
        if payload is None:
            print("Invalid card update JSON (first pass):", response.text)
            strict_prompt = _build_card_update_prompt(
                adventure,
                entries_to_compact,
                strict_json=True,
            )
            response = client.generate(prompt=strict_prompt, max_tokens=strict_max_tokens)
            payload = _extract_json_payload(response.text)
        if payload is None:
            print("Invalid card update JSON (strict pass):", response.text)
            return visible_entries[-max_posts:]
        _apply_card_updates(
            adventure,
            payload,
            source_history_entry=entries_to_compact[-1] if entries_to_compact else None,
        )
        next_index = min(len(entries_to_compact), len(visible_entries) - 1)
        adventure.rollback_min_history_id = visible_entries[next_index].id
        adventure.save(update_fields=["rollback_min_history_id"])
        visible_entries = visible_entries[next_index:]

    return visible_entries


def _set_ai_waiting(adventure_id: int, waiting: bool) -> None:
    Adventure.objects.filter(id=adventure_id).update(is_waiting_ai=waiting)
