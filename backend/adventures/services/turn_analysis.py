"""Opt-in LLM analysis for growth support and durable narrative consequences."""
from __future__ import annotations

import json

from django.contrib.auth import get_user_model
from django.db import transaction

from backend.llm import LLMClient, get_llm_client

from ..models import (
    Adventure,
    AdventureEvent,
    AdventureHistory,
    BehaviorEvidence,
    Character,
    ConsequenceMarker,
    Faction,
    LearningObjective,
    Location,
    NarrativeConsequence,
    RepairOpportunity,
    SafetyReview,
    TurnAnalysisLog,
)
from ..schemas.llm import (
    EvidenceItem,
    NarrativeConsequenceItem,
    TurnAnalysis,
    is_json_object_output,
    parse_json_object_output,
    parse_turn_analysis_output,
)
from .evaluation import ALLOWED_COMPETENCIES, save_evidence
from .narrative_consequences import (
    MAX_ENTITY_TITLE_CHARS,
    apply_narrative_consequence_updates,
    get_current_entity_scope,
    get_relevant_narrative_consequences,
    restore_narrative_consequence_snapshot,
    snapshot_narrative_consequence,
)


def _trim(value: object, limit: int) -> str:
    return str(value or "").strip()[:limit]


def _history_context(adventure: Adventure) -> list[dict]:
    entries = AdventureHistory.objects.filter(adventure=adventure).order_by("-id")[:5]
    return [
        {"id": entry.id, "role": entry.role, "content": entry.content[:1200]}
        for entry in reversed(list(entries))
    ]


def _entity_catalog(adventure: Adventure) -> dict:
    characters = (
        Character.objects.filter(adventure=adventure)
        .order_by("title")
        .values("id", "title", "location_id", "story_status")[:80]
    )
    locations = Location.objects.filter(adventure=adventure).order_by("title").values("id", "title")[
        :50
    ]
    factions = Faction.objects.filter(adventure=adventure).order_by("title").values("id", "title")[
        :50
    ]
    return {
        "characters": [
            {**item, "title": _trim(item["title"], MAX_ENTITY_TITLE_CHARS)}
            for item in characters
        ],
        "locations": [
            {**item, "title": _trim(item["title"], MAX_ENTITY_TITLE_CHARS)}
            for item in locations
        ],
        "factions": [
            {**item, "title": _trim(item["title"], MAX_ENTITY_TITLE_CHARS)}
            for item in factions
        ],
    }


def _event_catalog(adventure: Adventure) -> list[dict]:
    return list(
        AdventureEvent.objects.filter(adventure=adventure)
        .order_by("id")
        .values("id", "title", "status", "state")[:50]
    )


def _existing_consequence_context(adventure: Adventure) -> list[dict]:
    current_location_id, character_ids, faction_ids = get_current_entity_scope(adventure)
    return get_relevant_narrative_consequences(
        adventure,
        current_location_id=current_location_id,
        character_ids=character_ids,
        faction_ids=faction_ids,
        limit=8,
        include_unestablished=True,
    )


def _active_growth_objectives(adventure: Adventure) -> list[dict]:
    if not adventure.growth_analysis_enabled:
        return []
    return list(
        LearningObjective.objects.filter(adventure=adventure, is_active=True)
        .order_by("-weight", "id")
        .values("competency", "title", "description")[:8]
    )


def _turn_analysis_enabled(adventure: Adventure) -> bool:
    return adventure.narrative_consequences_enabled or bool(_active_growth_objectives(adventure))


def _build_turn_analysis_prompt(adventure: Adventure, history_entry: AdventureHistory) -> str:
    objectives = _active_growth_objectives(adventure)
    objectives = [
        {
            **objective,
            "title": _trim(objective["title"], 160),
            "description": _trim(objective["description"], 500),
        }
        for objective in objectives
    ]
    schema_sections = []
    feature_rules = []
    feature_context = []
    growth_active = bool(objectives)
    if growth_active:
        competencies = "|".join(sorted({objective["competency"] for objective in objectives}))
        schema_sections.extend(
            [
                (
                    f"\"evidence\":[{{\"competency\":\"{competencies}\","
                    "\"marker\":\"brief_observable_marker\",\"score\":-2,\"confidence\":0.0,"
                    "\"excerpt\":\"exact quote from the latest player turn\","
                    "\"rationale\":\"observable reason\"}]"
                ),
                (
                    "\"repair_opportunities\":[{\"competency\":\"...\","
                    "\"title\":\"in-world opportunity\","
                    "\"description\":\"concrete impact in this fiction\","
                    "\"suggested_action\":\"plausible in-world opening\"}]"
                ),
            ]
        )
        feature_rules.extend(
            [
                "- Evidence and repair opportunities are enabled for this scenario.\n",
                "- A repair opportunity must be an organic story opening, not a forced confession or punishment.\n",
            ]
        )
        feature_context.append(
            f"Scenario growth objectives: {json.dumps(objectives, ensure_ascii=False)}\n"
        )
    if adventure.narrative_consequences_enabled:
        schema_sections.append(
            "\"narrative_consequences\":[{\"id\":1,\"certainty\":\"intent|attempted\","
            "\"title\":\"brief event title\","
            "\"summary\":\"factual summary of an action or world event worth "
            "remembering for later scenes\",\"importance\":1,\"characters\":[1],"
            "\"locations\":[2],\"factions\":[3]}]"
        )
        feature_rules.extend(
            [
                "- Narrative consequences are enabled for this scenario.\n",
                "- Store a narrative consequence only when a later scene could plausibly react to it.\n",
                "- Preserve moral cause and effect: remember meaningful kindness, honesty, loyalty, courage, responsibility, cruelty, exploitation, betrayal, and selfish harm when the fiction supports it.\n",
                "- Keep enough factual detail for later scenes to make good actions more rewarding and harmful actions more costly through interesting story developments.\n",
                "- The latest player turn is a declaration of character action, not authoritative world narration. Store requested or conditional outcomes as intent. Store only actions directly performed by the character as attempted.\n",
                "- Never claim that a requested blessing, injury, death, victory, location change, NPC reaction, or other world outcome already happened unless it was established in the recent story context.\n",
                "- Prefer updating an existing consequence by id when the latest turn advances the same durable thread. Return no more than three narrative consequences.\n",
                "- Link only entity IDs from the supplied catalog. Omit uncertain links.\n",
                "- Do not restate an existing consequence unless the latest turn materially changes it.\n",
            ]
        )
        feature_context.extend(
            [
                f"Entity catalog: {json.dumps(_entity_catalog(adventure), ensure_ascii=False)}\n",
                (
                    "Existing relevant consequence memory: "
                    f"{json.dumps(_existing_consequence_context(adventure), ensure_ascii=False)}\n"
                ),
            ]
        )
    return (
        "Analyze one player turn in an immersive narrative game.\n"
        "Return only valid JSON, without markdown or commentary.\n"
        "The game can use any setting, including entertainment-first fantasy. Preserve immersion.\n"
        f"Schema:\n{{{','.join(schema_sections)}}}\n"
        "Rules:\n"
        "- Analyze observable events in the fiction, not the player's personality or hidden motives.\n"
        "- Empty arrays are valid and preferred for routine turns.\n"
        "- Preserve immersion: express psychological and moral development through the game world and its consequences.\n"
        "- Keep human-readable text values in the language used by the story context.\n"
        f"{''.join(feature_rules)}\n"
        f"growth_analysis_enabled={json.dumps(growth_active)}\n"
        f"narrative_consequences_enabled={json.dumps(adventure.narrative_consequences_enabled)}\n"
        f"Latest player turn ID: {history_entry.id}\n"
        f"Latest player turn: {history_entry.content[:2500]}\n"
        f"Recent story context: {json.dumps(_history_context(adventure), ensure_ascii=False)}\n"
        f"{''.join(feature_context)}"
    )


def _filter_evidence(
    items: list[EvidenceItem],
    player_text: str,
    *,
    allowed_competencies: set[str],
) -> list[EvidenceItem]:
    filtered = []
    lowered = player_text.lower()
    for item in items[:8]:
        excerpt = item.excerpt.strip()
        if item.competency not in allowed_competencies:
            continue
        if not item.marker or len(item.marker) > 128 or item.confidence < 0.55:
            continue
        if not excerpt or excerpt.lower() not in lowered:
            continue
        filtered.append(item)
    return filtered


def _request_turn_analysis(
    adventure: Adventure,
    history_entry: AdventureHistory,
    *,
    client: LLMClient | None = None,
) -> tuple[TurnAnalysis, str, bool]:
    if not _turn_analysis_enabled(adventure):
        return TurnAnalysis(), "", True
    llm_client = client or get_llm_client()
    response = llm_client.generate(
        prompt=_build_turn_analysis_prompt(adventure, history_entry),
        system=(
            "You are a restrained narrative-state analyst. Preserve immersion, output only "
            "supported structured observations, and prefer empty arrays over speculation."
        ),
        max_tokens=1400,
        temperature=0.0,
    )
    parsed = parse_turn_analysis_output(response.text)
    active_competencies = {
        objective["competency"] for objective in _active_growth_objectives(adventure)
    }
    return TurnAnalysis(
        evidence=_filter_evidence(
            parsed.evidence,
            history_entry.content,
            allowed_competencies=active_competencies,
        )
        if active_competencies
        else [],
        repair_opportunities=[
            item for item in parsed.repair_opportunities if item.competency in active_competencies
        ]
        if active_competencies
        else [],
        narrative_consequences=parsed.narrative_consequences
        if adventure.narrative_consequences_enabled
        else [],
    ), response.text, is_json_object_output(response.text)


def analyze_turn(
    adventure: Adventure,
    history_entry: AdventureHistory,
    *,
    client: LLMClient | None = None,
) -> TurnAnalysis:
    analysis, _, _ = _request_turn_analysis(adventure, history_entry, client=client)
    return analysis


def _consequence_payload(
    items: list[NarrativeConsequenceItem],
    *,
    player_declared: bool = False,
) -> list[dict]:
    def certainty(item: NarrativeConsequenceItem) -> str:
        if not player_declared:
            return NarrativeConsequence.Certainty.ESTABLISHED
        if item.certainty == NarrativeConsequence.Certainty.INTENT:
            return NarrativeConsequence.Certainty.INTENT
        return NarrativeConsequence.Certainty.ATTEMPTED

    return [
        {
            "id": item.id,
            "status": item.status,
            "certainty": certainty(item),
            "title": item.title,
            "summary": item.summary,
            "importance": item.importance,
            "characters": item.characters,
            "locations": item.locations,
            "factions": item.factions,
        }
        for item in items[:3]
    ]


def _find_existing_consequence(adventure: Adventure, item: dict) -> NarrativeConsequence | None:
    try:
        consequence_id = int(item.get("id")) if item.get("id") is not None else None
    except (TypeError, ValueError):
        consequence_id = None
    if consequence_id:
        consequence = NarrativeConsequence.objects.filter(
            adventure=adventure,
            id=consequence_id,
        ).first()
        if consequence is not None:
            return consequence
    title = str(item.get("title") or "").strip()
    if not title:
        return None
    return NarrativeConsequence.objects.filter(adventure=adventure, title=title).first()


def _snapshot_narrative_updates(adventure: Adventure, payload: list[dict]) -> dict:
    previous = []
    previous_ids = set()
    for item in payload:
        consequence = _find_existing_consequence(adventure, item)
        if consequence is None or consequence.id in previous_ids:
            continue
        previous.append(snapshot_narrative_consequence(consequence))
        previous_ids.add(consequence.id)
    return {"narrative_previous": previous, "_narrative_previous_ids": previous_ids}


def _finish_narrative_snapshot(snapshot: dict, touched: list[NarrativeConsequence]) -> dict:
    previous_ids = snapshot.pop("_narrative_previous_ids", set())
    snapshot["narrative_created_ids"] = [
        consequence.id for consequence in touched if consequence.id not in previous_ids
    ]
    return snapshot


@transaction.atomic
def persist_turn_analysis(
    adventure: Adventure,
    user: get_user_model(),
    history_entry: AdventureHistory,
    analysis: TurnAnalysis,
) -> dict:
    active_competencies = {
        objective["competency"] for objective in _active_growth_objectives(adventure)
    }
    evidence = save_evidence(
        adventure,
        user,
        [item for item in analysis.evidence if item.competency in active_competencies],
        history_entry=history_entry,
    )
    evidence_by_competency = {}
    for item in evidence:
        evidence_by_competency.setdefault(item.competency, item)

    if active_competencies:
        for item in analysis.repair_opportunities[:8]:
            if item.competency not in active_competencies:
                continue
            RepairOpportunity.objects.get_or_create(
                adventure=adventure,
                user=user,
                source_history_entry=history_entry,
                title=item.title,
                defaults={
                    "source_evidence": evidence_by_competency.get(item.competency),
                    "competency": item.competency,
                    "description": item.description,
                    "suggested_action": item.suggested_action,
                },
            )

    payload = _consequence_payload(analysis.narrative_consequences, player_declared=True)
    snapshot = _snapshot_narrative_updates(adventure, payload)
    touched = apply_narrative_consequence_updates(
        adventure,
        payload,
        source_history_entry=history_entry,
        default_certainty=NarrativeConsequence.Certainty.ATTEMPTED,
        preserve_established=True,
    )
    return _finish_narrative_snapshot(snapshot, touched)


def _log_analysis(
    adventure: Adventure,
    history_entry: AdventureHistory,
    *,
    kind: str,
    status: str,
    raw_response: str = "",
    error: str = "",
    analysis: TurnAnalysis | None = None,
    snapshot: dict | None = None,
) -> None:
    counts = {}
    if analysis is not None:
        counts = {
            "evidence": len(analysis.evidence),
            "repair_opportunities": len(analysis.repair_opportunities),
            "narrative_consequences": len(analysis.narrative_consequences),
        }
    TurnAnalysisLog.objects.create(
        adventure=adventure,
        history_entry=history_entry,
        kind=kind,
        status=status,
        raw_response=raw_response[:12000],
        error=error[:2000],
        result_counts=counts,
        snapshot=snapshot or {},
    )


def analyze_and_persist_turn(
    adventure: Adventure,
    user: get_user_model(),
    history_entry: AdventureHistory,
    *,
    client: LLMClient | None = None,
) -> None:
    if not _turn_analysis_enabled(adventure):
        return
    try:
        analysis, raw_response, valid_output = _request_turn_analysis(
            adventure,
            history_entry,
            client=client,
        )
    except Exception as exc:
        _log_analysis(
            adventure,
            history_entry,
            kind=TurnAnalysisLog.Kind.PLAYER_TURN,
            status=TurnAnalysisLog.Status.ERROR,
            error=str(exc),
        )
        return
    if not valid_output:
        _log_analysis(
            adventure,
            history_entry,
            kind=TurnAnalysisLog.Kind.PLAYER_TURN,
            status=TurnAnalysisLog.Status.INVALID_OUTPUT,
            raw_response=raw_response,
        )
        return
    try:
        snapshot = persist_turn_analysis(adventure, user, history_entry, analysis)
    except Exception as exc:
        _log_analysis(
            adventure,
            history_entry,
            kind=TurnAnalysisLog.Kind.PLAYER_TURN,
            status=TurnAnalysisLog.Status.ERROR,
            raw_response=raw_response,
            error=str(exc),
            analysis=analysis,
        )
        return
    _log_analysis(
        adventure,
        history_entry,
        kind=TurnAnalysisLog.Kind.PLAYER_TURN,
        status=TurnAnalysisLog.Status.OK,
        raw_response=raw_response,
        analysis=analysis,
        snapshot=snapshot,
    )


def _build_world_confirmation_prompt(
    adventure: Adventure,
    history_entry: AdventureHistory,
) -> str:
    return (
        "Extract durable moral cause-and-effect facts from one newly generated world scene.\n"
        "Return only valid JSON, without markdown or commentary.\n"
        "Schema:\n"
        "{\"events\":[{\"id\":1,\"status\":\"active|resolved|inactive\",\"state\":\"confirmed world state\"}],"
        "\"characters\":[{\"id\":1,\"story_status\":\"active|dead|missing|inactive\"}],"
        "\"narrative_consequences\":[{\"id\":1,\"status\":\"active|resolved|archived\","
        "\"certainty\":\"established\",\"title\":\"brief event title\","
        "\"summary\":\"factual confirmed event worth remembering for later scenes\","
        "\"importance\":1,\"characters\":[1],\"locations\":[2],\"factions\":[3]}]}\n"
        "Rules:\n"
        "- Extract only outcomes explicitly established by the latest world narration.\n"
        "- Do not treat plans, threats, wishes, requests, conditional actions, or attempted actions as completed facts.\n"
        "- Prefer updating an existing intent or attempted consequence by id when the scene confirms, changes, resolves, or archives that thread.\n"
        "- Create a new consequence only for a durable confirmed event that later scenes could plausibly react to.\n"
        "- Update an existing event or character status only when the latest narration explicitly confirms the change. Never invent new cards.\n"
        "- Mark a character dead only when death is explicit. Mark missing or inactive only when the narration clearly establishes it.\n"
        "- Preserve moral cause and effect without adding a score, personality judgment, or mechanical punishment.\n"
        "- Keep human-readable text values in the language used by the story context.\n"
        "- Link only entity IDs from the supplied catalog. Omit uncertain links.\n"
        "- Return no more than three narrative consequences. Empty arrays are valid and preferred for routine scenes.\n"
        f"Latest world scene ID: {history_entry.id}\n"
        f"Latest world scene: {history_entry.content[:3000]}\n"
        f"Recent story context: {json.dumps(_history_context(adventure), ensure_ascii=False)}\n"
        f"Entity catalog: {json.dumps(_entity_catalog(adventure), ensure_ascii=False)}\n"
        f"Existing event catalog: {json.dumps(_event_catalog(adventure), ensure_ascii=False)}\n"
        "Existing relevant consequence memory, including unconfirmed threads: "
        f"{json.dumps(_existing_consequence_context(adventure), ensure_ascii=False)}\n"
    )


def _request_world_confirmation(
    adventure: Adventure,
    history_entry: AdventureHistory,
    *,
    client: LLMClient | None = None,
) -> tuple[TurnAnalysis, dict, str, bool]:
    if not adventure.narrative_consequences_enabled:
        return TurnAnalysis(), {}, "", True
    llm_client = client or get_llm_client()
    response = llm_client.generate(
        prompt=_build_world_confirmation_prompt(adventure, history_entry),
        system=(
            "You are a restrained narrative-state analyst. Record only facts established by "
            "world narration and prefer updating existing threads over creating duplicates."
        ),
        max_tokens=900,
        temperature=0.0,
    )
    payload = parse_json_object_output(response.text)
    parsed = parse_turn_analysis_output(response.text)
    return (
        TurnAnalysis(narrative_consequences=parsed.narrative_consequences),
        payload,
        response.text,
        is_json_object_output(response.text),
    )


def _apply_confirmed_world_updates(adventure: Adventure, payload: dict) -> dict:
    snapshot = {"events_previous": [], "characters_previous": []}
    events = payload.get("events", [])
    if isinstance(events, list):
        for item in events[:12]:
            if not isinstance(item, dict):
                continue
            try:
                event_id = int(item.get("id"))
            except (TypeError, ValueError):
                continue
            event = AdventureEvent.objects.filter(
                adventure=adventure,
                id=event_id,
            ).first()
            if event is None:
                continue
            snapshot["events_previous"].append(
                {"id": event.id, "status": event.status, "state": event.state}
            )
            update_fields = []
            if item.get("status") in AdventureEvent.Status.values:
                event.status = item["status"]
                update_fields.append("status")
            if isinstance(item.get("state"), str):
                event.state = item["state"][:4000]
                update_fields.append("state")
            if update_fields:
                event.save(update_fields=update_fields)

    characters = payload.get("characters", [])
    if isinstance(characters, list):
        for item in characters[:12]:
            if not isinstance(item, dict):
                continue
            try:
                character_id = int(item.get("id"))
            except (TypeError, ValueError):
                continue
            character = Character.objects.filter(
                adventure=adventure,
                id=character_id,
            ).first()
            if character is None or item.get("story_status") not in Character.StoryStatus.values:
                continue
            snapshot["characters_previous"].append(
                {
                    "id": character.id,
                    "story_status": character.story_status,
                    "in_party": character.in_party,
                }
            )
            character.story_status = item["story_status"]
            update_fields = ["story_status"]
            if character.story_status != Character.StoryStatus.ACTIVE and character.in_party:
                character.in_party = False
                update_fields.append("in_party")
            character.save(update_fields=update_fields)
    return snapshot


def analyze_and_persist_world_confirmation(
    adventure: Adventure,
    history_entry: AdventureHistory,
    *,
    client: LLMClient | None = None,
) -> None:
    if not adventure.narrative_consequences_enabled:
        return
    try:
        analysis, payload, raw_response, valid_output = _request_world_confirmation(
            adventure,
            history_entry,
            client=client,
        )
    except Exception as exc:
        _log_analysis(
            adventure,
            history_entry,
            kind=TurnAnalysisLog.Kind.WORLD_CONFIRMATION,
            status=TurnAnalysisLog.Status.ERROR,
            error=str(exc),
        )
        return
    if not valid_output:
        _log_analysis(
            adventure,
            history_entry,
            kind=TurnAnalysisLog.Kind.WORLD_CONFIRMATION,
            status=TurnAnalysisLog.Status.INVALID_OUTPUT,
            raw_response=raw_response,
        )
        return
    try:
        with transaction.atomic():
            snapshot = _apply_confirmed_world_updates(adventure, payload)
            consequence_payload = _consequence_payload(analysis.narrative_consequences)
            snapshot.update(_snapshot_narrative_updates(adventure, consequence_payload))
            touched = apply_narrative_consequence_updates(
                adventure,
                consequence_payload,
                source_history_entry=history_entry,
                default_certainty=NarrativeConsequence.Certainty.ESTABLISHED,
            )
            snapshot = _finish_narrative_snapshot(snapshot, touched)
    except Exception as exc:
        _log_analysis(
            adventure,
            history_entry,
            kind=TurnAnalysisLog.Kind.WORLD_CONFIRMATION,
            status=TurnAnalysisLog.Status.ERROR,
            raw_response=raw_response,
            error=str(exc),
            analysis=analysis,
        )
        return
    _log_analysis(
        adventure,
        history_entry,
        kind=TurnAnalysisLog.Kind.WORLD_CONFIRMATION,
        status=TurnAnalysisLog.Status.OK,
        raw_response=raw_response,
        analysis=analysis,
        snapshot=snapshot,
    )


def _restore_analysis_snapshot(adventure: Adventure, snapshot: dict) -> None:
    NarrativeConsequence.objects.filter(
        adventure=adventure,
        id__in=snapshot.get("narrative_created_ids", []),
    ).delete()
    for item in reversed(snapshot.get("narrative_previous", [])):
        if isinstance(item, dict):
            restore_narrative_consequence_snapshot(adventure, item)
    for item in reversed(snapshot.get("events_previous", [])):
        if not isinstance(item, dict):
            continue
        event = AdventureEvent.objects.filter(adventure=adventure, id=item.get("id")).first()
        if event is None:
            continue
        event.status = item.get("status", event.status)
        event.state = item.get("state", event.state)
        event.save(update_fields=["status", "state"])
    for item in reversed(snapshot.get("characters_previous", [])):
        if not isinstance(item, dict):
            continue
        character = Character.objects.filter(adventure=adventure, id=item.get("id")).first()
        if character is None:
            continue
        character.story_status = item.get("story_status", character.story_status)
        character.in_party = bool(item.get("in_party", character.in_party))
        character.save(update_fields=["story_status", "in_party"])


@transaction.atomic
def revert_analysis_for_history_entries(
    adventure: Adventure,
    history_entries: list[AdventureHistory],
) -> None:
    history_entry_ids = [entry.id for entry in history_entries]
    if not history_entry_ids:
        return
    logs = list(
        TurnAnalysisLog.objects.filter(
            adventure=adventure,
            history_entry_id__in=history_entry_ids,
        ).order_by("-created_at", "-id")
    )
    for log in logs:
        if isinstance(log.snapshot, dict):
            _restore_analysis_snapshot(adventure, log.snapshot)
    BehaviorEvidence.objects.filter(
        adventure=adventure,
        history_entry_id__in=history_entry_ids,
    ).delete()
    RepairOpportunity.objects.filter(
        adventure=adventure,
        source_history_entry_id__in=history_entry_ids,
    ).delete()
    ConsequenceMarker.objects.filter(
        adventure=adventure,
        history_entry_id__in=history_entry_ids,
    ).delete()
    SafetyReview.objects.filter(
        adventure=adventure,
        history_entry_id__in=history_entry_ids,
    ).delete()
    NarrativeConsequence.objects.filter(
        adventure=adventure,
        source_history_entry_id__in=history_entry_ids,
    ).delete()
    TurnAnalysisLog.objects.filter(id__in=[log.id for log in logs]).delete()
