"""Growth objective, intervention, choice-card, and reflection selection."""
from __future__ import annotations

from dataclasses import dataclass

from django.contrib.auth import get_user_model
from django.db.models import Q

from ..models import (
    Adventure,
    AdventureEvent,
    AdventureHistory,
    AdventureMemory,
    BehaviorEvidence,
    CharacterRelationship,
    ConsequenceMarker,
    LearningObjective,
    PedagogicalIntervention,
    ReflectionPrompt,
    ReflectionResponse,
    RepairOpportunity,
)
from .localization import normalize_locale


COMPETENCY_SIGNALS = {
    "empathy": (
        "empathy",
        "feel",
        "listen",
        "поним",
        "чувств",
        "выслуш",
        "сопереж",
        "理解",
        "感受",
    ),
    "cooperation": (
        "cooperate",
        "together",
        "team",
        "команд",
        "вместе",
        "договор",
        "соглас",
        "合作",
        "一起",
    ),
    "self_regulation": (
        "calm",
        "pause",
        "breathe",
        "спокой",
        "пауза",
        "подожд",
        "выдох",
        "冷静",
    ),
    "responsible_decision": (
        "responsib",
        "consequence",
        "plan",
        "ответствен",
        "последств",
        "план",
        "решени",
        "负责",
    ),
    "restorative_action": (
        "repair",
        "apolog",
        "trust",
        "исправ",
        "извин",
        "довер",
        "возмест",
        "修复",
        "道歉",
    ),
    "help_seeking": (
        "help",
        "teacher",
        "adult",
        "помощ",
        "учител",
        "взросл",
        "настав",
        "帮助",
        "老师",
    ),
    "inclusion": (
        "include",
        "accessible",
        "accommod",
        "включ",
        "доступ",
        "удоб",
        "исключ",
        "包容",
        "照顾",
    ),
}

OPEN_REPAIR_STATUSES = (
    RepairOpportunity.Status.OPEN,
    RepairOpportunity.Status.IN_PROGRESS,
)
RECENT_STATE_LIMIT = 20


@dataclass(frozen=True)
class GrowthDirectorDecision:
    objective: LearningObjective | None
    objectives: list[LearningObjective]
    interventions: list[PedagogicalIntervention]
    competency_scores: dict[str, int]
    state_notes: list[str]
    should_offer_reflection: bool
    reflection_reason: str = ""


def _user_scope(user: get_user_model() | None) -> Q:
    if user is None:
        return Q()
    return Q(user=user) | Q(user__isnull=True)


def _matches_competency(text: str, competency: str) -> bool:
    lowered = (text or "").lower()
    if not lowered:
        return False
    return any(signal in lowered for signal in COMPETENCY_SIGNALS.get(competency, ()))


def _bump_score(
    scores: dict[str, int],
    notes: list[str],
    competency: str | None,
    amount: int,
    note: str = "",
) -> None:
    if not competency:
        return
    scores[competency] = scores.get(competency, 0) + amount
    if note and note not in notes and len(notes) < 8:
        notes.append(note)


def _objective_score(objective: LearningObjective, scores: dict[str, int]) -> int:
    return objective.weight * 10 + scores.get(objective.competency, 0)


def _rank_objectives(
    objectives: list[LearningObjective],
    scores: dict[str, int],
) -> list[LearningObjective]:
    return sorted(
        objectives,
        key=lambda objective: (
            _objective_score(objective, scores),
            objective.weight,
            -objective.id,
        ),
        reverse=True,
    )


def _recent_text_has_signal(adventure: Adventure, competency: str) -> bool:
    recent_entries = AdventureHistory.objects.filter(
        adventure=adventure,
        role=AdventureHistory.Role.USER,
    ).order_by("-id")[:RECENT_STATE_LIMIT]
    return any(_matches_competency(entry.content, competency) for entry in recent_entries)


def _collect_state_scores(
    adventure: Adventure,
    *,
    user: get_user_model() | None = None,
) -> tuple[dict[str, int], list[str]]:
    scores: dict[str, int] = {}
    notes: list[str] = []

    repairs = RepairOpportunity.objects.filter(adventure=adventure).filter(_user_scope(user))
    for repair in repairs.filter(status__in=OPEN_REPAIR_STATUSES).order_by("-created_at")[
        :RECENT_STATE_LIMIT
    ]:
        amount = 34 if repair.status == RepairOpportunity.Status.OPEN else 24
        _bump_score(
            scores,
            notes,
            repair.competency,
            amount,
            f"open repair path: {repair.title}",
        )

    evidence = BehaviorEvidence.objects.filter(adventure=adventure)
    if user is not None:
        evidence = evidence.filter(user=user)
    for item in evidence.order_by("-created_at")[:RECENT_STATE_LIMIT]:
        if item.score < 0:
            _bump_score(
                scores,
                notes,
                item.competency,
                22,
                f"recent growth opportunity: {item.competency}",
            )
        elif item.score > 0:
            _bump_score(scores, notes, item.competency, 7)

    markers = ConsequenceMarker.objects.filter(adventure=adventure).filter(_user_scope(user))
    for marker in markers.order_by("-created_at")[:RECENT_STATE_LIMIT]:
        if marker.kind in {
            ConsequenceMarker.Kind.REPAIR_OPENED,
            ConsequenceMarker.Kind.GROWTH_OPPORTUNITY,
        }:
            _bump_score(
                scores,
                notes,
                marker.competency,
                18,
                f"active consequence: {marker.title}",
            )
        elif marker.kind == ConsequenceMarker.Kind.CONSTRUCTIVE_CHOICE:
            _bump_score(scores, notes, marker.competency, 6)

    active_events = AdventureEvent.objects.filter(
        adventure=adventure,
        status=AdventureEvent.Status.ACTIVE,
    ).order_by("id")[:RECENT_STATE_LIMIT]
    for event in active_events:
        text = f"{event.title} {event.trigger_hint} {event.state}"
        for competency in COMPETENCY_SIGNALS:
            if _matches_competency(text, competency):
                _bump_score(
                    scores,
                    notes,
                    competency,
                    10,
                    f"active story event: {event.title}",
                )

    memories = AdventureMemory.objects.filter(adventure=adventure).order_by(
        "-importance",
        "-updated_at",
    )[:RECENT_STATE_LIMIT]
    for memory in memories:
        text = f"{memory.title} {memory.content} {' '.join(memory.tags)}"
        for competency in COMPETENCY_SIGNALS:
            if _matches_competency(text, competency):
                _bump_score(scores, notes, competency, 5)

    relationships = CharacterRelationship.objects.filter(
        from_character__adventure=adventure,
    ).order_by("-updated_at")[:RECENT_STATE_LIMIT]
    for relationship in relationships:
        text = f"{relationship.kind} {relationship.description}"
        for competency in COMPETENCY_SIGNALS:
            if _matches_competency(text, competency):
                _bump_score(scores, notes, competency, 8)

    for competency in COMPETENCY_SIGNALS:
        if _recent_text_has_signal(adventure, competency):
            _bump_score(scores, notes, competency, 9)

    return scores, notes


def _reflection_trigger_reason(
    adventure: Adventure,
    objectives: list[LearningObjective],
    *,
    user: get_user_model() | None,
) -> str:
    if user is None:
        return ""
    user_turns = AdventureHistory.objects.filter(
        adventure=adventure,
        role=AdventureHistory.Role.USER,
    )
    if not user_turns.exists():
        return ""
    if RepairOpportunity.objects.filter(
        adventure=adventure,
        status__in=OPEN_REPAIR_STATUSES,
    ).filter(_user_scope(user)).exists():
        return "open repair opportunity"
    if BehaviorEvidence.objects.filter(adventure=adventure, user=user).order_by(
        "-created_at"
    ).exists():
        return "recent observable evidence"
    if ConsequenceMarker.objects.filter(adventure=adventure).filter(_user_scope(user)).order_by(
        "-created_at"
    ).exists():
        return "recent story consequence"
    for objective in objectives:
        if _recent_text_has_signal(adventure, objective.competency):
            return f"recent story signal: {objective.competency}"
    if user_turns.count() >= 4:
        return "session checkpoint"
    return ""


def get_growth_director_decision(
    adventure: Adventure,
    *,
    user: get_user_model() | None = None,
    include_choice_cards: bool = False,
) -> GrowthDirectorDecision:
    if not adventure.growth_analysis_enabled:
        return GrowthDirectorDecision(
            objective=None,
            objectives=[],
            interventions=[],
            competency_scores={},
            state_notes=[],
            should_offer_reflection=False,
        )
    objectives = list(
        LearningObjective.objects.filter(adventure=adventure, is_active=True).order_by(
            "-weight",
            "id",
        )
    )
    scores, state_notes = _collect_state_scores(adventure, user=user)
    ranked_objectives = _rank_objectives(objectives, scores)
    objective = ranked_objectives[0] if ranked_objectives else None

    interventions = list(
        PedagogicalIntervention.objects.filter(adventure=adventure, is_active=True)
        .select_related("objective")
        .order_by("id")
    )
    if not include_choice_cards:
        interventions = [
            intervention
            for intervention in interventions
            if intervention.kind != PedagogicalIntervention.Kind.CHOICE_CARDS
        ]
    interventions.sort(
        key=lambda intervention: (
            _objective_score(intervention.objective, scores),
            intervention.objective.weight,
            -intervention.id,
        ),
        reverse=True,
    )

    reflection_reason = _reflection_trigger_reason(
        adventure,
        ranked_objectives,
        user=user,
    )
    return GrowthDirectorDecision(
        objective=objective,
        objectives=ranked_objectives,
        interventions=interventions[:6],
        competency_scores={
            objective.competency: _objective_score(objective, scores)
            for objective in ranked_objectives
        },
        state_notes=state_notes,
        should_offer_reflection=bool(reflection_reason),
        reflection_reason=reflection_reason,
    )


def choose_objective(adventure: Adventure) -> LearningObjective | None:
    return get_growth_director_decision(adventure).objective


def choose_reflection_prompt(
    adventure: Adventure,
    *,
    user: get_user_model(),
) -> ReflectionPrompt | None:
    decision = get_growth_director_decision(adventure, user=user)
    if not decision.should_offer_reflection:
        return None
    answered_ids = ReflectionResponse.objects.filter(
        adventure=adventure,
        user=user,
    ).values_list("prompt_id", flat=True)
    prompts = list(
        ReflectionPrompt.objects.filter(adventure=adventure, is_active=True)
        .exclude(id__in=answered_ids)
        .select_related("objective")
        .order_by("id")
    )
    if not prompts:
        return None
    prompts.sort(
        key=lambda prompt: (
            decision.competency_scores.get(prompt.objective.competency, 0),
            prompt.objective_id == (decision.objective.id if decision.objective else None),
            _recent_text_has_signal(adventure, prompt.objective.competency),
            -prompt.id,
        ),
        reverse=True,
    )
    return prompts[0]


def get_choice_cards(adventure: Adventure, locale: str | None = None) -> list[str]:
    decision = get_growth_director_decision(adventure, include_choice_cards=True)
    intervention = next(
        (
            candidate
            for candidate in decision.interventions
            if candidate.kind == PedagogicalIntervention.Kind.CHOICE_CARDS
        ),
        None,
    )
    if not intervention:
        return []
    cards = intervention.payload.get("cards", [])
    if isinstance(cards, dict):
        normalized = normalize_locale(locale)
        cards = cards.get(normalized) or cards.get("ru") or cards.get("en") or []
    if not isinstance(cards, list):
        return []
    return [str(card) for card in cards if str(card).strip()][:6]
