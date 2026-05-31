"""Rule-based safety layer for the educational MVP."""
from __future__ import annotations

from dataclasses import dataclass

from django.contrib.auth import get_user_model

from ..models import Adventure, AdventureHistory, ConsequenceMarker, SafetyReview


@dataclass(frozen=True)
class SafetyResult:
    risk_level: str
    categories: list[str]
    action: str
    notes: str


BLOCK_TERMS = {
    "self_harm": ("самоуб", "suicide", "kill myself", "自杀"),
    "sexual": ("изнас", "rape", "sexual", "色情"),
    "extremism": ("террор", "terror", "extremis", "恐怖主义"),
}

WARN_TERMS = {
    "bullying": ("трав", "булл", "bully", "欺凌"),
    "violence": ("убью", "kill", "attack", "打"),
}


def review_text(
    adventure: Adventure,
    text: str,
    *,
    user: get_user_model() | None = None,
    source: str,
    history_entry: AdventureHistory | None = None,
    persist: bool = True,
    persist_warnings: bool = True,
) -> SafetyResult:
    lowered = text.lower()
    categories: list[str] = []
    action = "allow"
    risk_level = "low"
    for category, terms in BLOCK_TERMS.items():
        if any(term in lowered for term in terms):
            categories.append(category)
            action = "block"
            risk_level = "high"
    if action != "block":
        for category, terms in WARN_TERMS.items():
            if any(term in lowered for term in terms):
                categories.append(category)
        if categories:
            action = "warn"
            risk_level = "medium"
    notes = "Rule-based MVP review."
    review = None
    should_persist = persist or action == "block" or (persist_warnings and action == "warn")
    if should_persist:
        review = SafetyReview.objects.create(
            adventure=adventure,
            user=user,
            history_entry=history_entry,
            source=source,
            risk_level=risk_level,
            categories=categories,
            action=action,
            notes=notes,
        )
    if review and action == "warn" and history_entry is not None:
        title = "Safety-sensitive story moment"
        description = (
            "Scene may need safer handling: "
            + ", ".join(categories)
            + ". Keep agency, de-escalation, support, and repair paths available."
        )
        ConsequenceMarker.objects.get_or_create(
            adventure=adventure,
            user=user,
            history_entry=history_entry,
            kind=ConsequenceMarker.Kind.SAFETY_WARNING,
            defaults={
                "title": title,
                "description": description,
                "weight": -1,
                "tags": ["safety", *categories],
            },
        )
    return SafetyResult(
        risk_level=risk_level,
        categories=categories,
        action=action,
        notes=notes,
    )
