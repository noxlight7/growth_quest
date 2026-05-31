"""Orchestration helpers around the existing story-generation flow."""
from __future__ import annotations

from django.contrib.auth import get_user_model

from ..models import Adventure, AdventureHistory
from .pedagogy import choose_reflection_prompt
from .safety import SafetyResult, review_text
from .turn_analysis import analyze_and_persist_turn, analyze_and_persist_world_confirmation


def before_user_turn(adventure: Adventure, user: get_user_model(), content: str) -> SafetyResult:
    return review_text(
        adventure,
        content,
        user=user,
        source="input",
        persist=False,
        persist_warnings=False,
    )


def after_user_turn(
    adventure: Adventure,
    user: get_user_model(),
    history_entry: AdventureHistory,
) -> None:
    review_text(
        adventure,
        history_entry.content,
        user=user,
        source="input",
        history_entry=history_entry,
        persist=False,
    )
    analyze_and_persist_turn(adventure, user, history_entry)


def after_ai_turn(adventure: Adventure, history_entry: AdventureHistory | None) -> None:
    if history_entry is None:
        return
    review_text(
        adventure,
        history_entry.content,
        user=None,
        source="output",
        history_entry=history_entry,
        persist=False,
    )
    analyze_and_persist_world_confirmation(adventure, history_entry)


def pending_reflection(adventure: Adventure, user: get_user_model()):
    return choose_reflection_prompt(adventure, user=user)
