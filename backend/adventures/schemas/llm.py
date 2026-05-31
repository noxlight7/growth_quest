"""Small validation helpers for AI-assisted educational outputs."""
from __future__ import annotations

from dataclasses import dataclass, field
import json
from typing import Any


@dataclass(frozen=True)
class EvidenceItem:
    competency: str
    marker: str
    score: int
    confidence: float
    excerpt: str = ""
    rationale: str = ""


@dataclass(frozen=True)
class SafetyDecision:
    risk_level: str = "low"
    categories: list[str] = field(default_factory=list)
    action: str = "allow"
    notes: str = ""


@dataclass(frozen=True)
class RepairSuggestion:
    competency: str
    title: str
    description: str = ""
    suggested_action: str = ""


@dataclass(frozen=True)
class NarrativeConsequenceItem:
    title: str
    summary: str
    id: int | None = None
    status: str = "active"
    certainty: str = "established"
    importance: int = 1
    characters: list[int] = field(default_factory=list)
    locations: list[int] = field(default_factory=list)
    factions: list[int] = field(default_factory=list)


@dataclass(frozen=True)
class TurnAnalysis:
    evidence: list[EvidenceItem] = field(default_factory=list)
    repair_opportunities: list[RepairSuggestion] = field(default_factory=list)
    narrative_consequences: list[NarrativeConsequenceItem] = field(default_factory=list)


def _parse_json_value(raw_text: str) -> Any:
    cleaned = str(raw_text or "").strip()
    cleaned = cleaned.replace("```json", "").replace("```", "").strip()
    try:
        payload = json.loads(cleaned)
    except (TypeError, json.JSONDecodeError):
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return {}
        try:
            payload = json.loads(cleaned[start : end + 1])
        except (TypeError, json.JSONDecodeError):
            return {}
    return payload


def _parse_json_object(raw_text: str) -> dict:
    payload = _parse_json_value(raw_text)
    return payload if isinstance(payload, dict) else {}


def parse_json_object_output(raw_text: str) -> dict:
    return _parse_json_object(raw_text)


def is_json_object_output(raw_text: str) -> bool:
    return bool(_parse_json_object(raw_text))


def _parse_id_list(value: Any) -> list[int]:
    if not isinstance(value, list):
        return []
    result = []
    for item in value[:20]:
        try:
            result.append(int(item))
        except (TypeError, ValueError):
            continue
    return result


def parse_evaluator_output(raw_text: str) -> list[EvidenceItem]:
    """Parse evaluator JSON without letting malformed model output break the turn."""
    payload = _parse_json_value(raw_text)
    raw_items: Any = payload.get("evidence", []) if isinstance(payload, dict) else payload
    if not isinstance(raw_items, list):
        return []
    items: list[EvidenceItem] = []
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        competency = str(item.get("competency", "")).strip()
        marker = str(item.get("marker", "")).strip()
        if not competency or not marker:
            continue
        try:
            score = max(-2, min(2, int(item.get("score", 0))))
        except (TypeError, ValueError):
            score = 0
        try:
            confidence = max(0.0, min(1.0, float(item.get("confidence", 0.5))))
        except (TypeError, ValueError):
            confidence = 0.5
        items.append(
            EvidenceItem(
                competency=competency,
                marker=marker,
                score=score,
                confidence=confidence,
                excerpt=str(item.get("excerpt", ""))[:500],
                rationale=str(item.get("rationale", ""))[:500],
            )
        )
    return items


def parse_turn_analysis_output(raw_text: str) -> TurnAnalysis:
    """Parse bounded turn analysis output while ignoring malformed optional sections."""
    payload = _parse_json_object(raw_text)
    evidence = parse_evaluator_output(json.dumps({"evidence": payload.get("evidence", [])}))

    raw_repairs = payload.get("repair_opportunities", [])
    if not isinstance(raw_repairs, list):
        raw_repairs = []
    repairs = []
    for item in raw_repairs[:8]:
        if not isinstance(item, dict):
            continue
        competency = str(item.get("competency", "")).strip()
        title = str(item.get("title", "")).strip()[:200]
        if not competency or not title:
            continue
        repairs.append(
            RepairSuggestion(
                competency=competency,
                title=title,
                description=str(item.get("description", "")).strip()[:800],
                suggested_action=str(item.get("suggested_action", "")).strip()[:800],
            )
        )

    raw_consequences = payload.get("narrative_consequences", [])
    if not isinstance(raw_consequences, list):
        raw_consequences = []
    consequences = []
    for item in raw_consequences[:8]:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title", "")).strip()[:200]
        summary = str(item.get("summary", "")).strip()[:1200]
        if not title or not summary:
            continue
        try:
            importance = max(1, min(5, int(item.get("importance", 1))))
        except (TypeError, ValueError):
            importance = 1
        try:
            consequence_id = int(item["id"]) if item.get("id") is not None else None
        except (TypeError, ValueError):
            consequence_id = None
        consequences.append(
            NarrativeConsequenceItem(
                title=title,
                summary=summary,
                id=consequence_id,
                status=str(item.get("status", "active")).strip(),
                certainty=str(item.get("certainty", "established")).strip(),
                importance=importance,
                characters=_parse_id_list(item.get("characters")),
                locations=_parse_id_list(item.get("locations")),
                factions=_parse_id_list(item.get("factions")),
            )
        )

    return TurnAnalysis(
        evidence=evidence,
        repair_opportunities=repairs,
        narrative_consequences=consequences,
    )


def parse_safety_output(raw_text: str) -> SafetyDecision:
    payload = _parse_json_object(raw_text)
    if not payload:
        return SafetyDecision(notes="Fallback: moderation JSON was invalid.")
    if not isinstance(payload, dict):
        return SafetyDecision(notes="Fallback: moderation output was not an object.")
    action = str(payload.get("action", "allow"))
    if action not in {"allow", "warn", "block"}:
        action = "allow"
    risk_level = str(payload.get("risk_level", "low"))
    if risk_level not in {"low", "medium", "high"}:
        risk_level = "low"
    categories = payload.get("categories", [])
    if not isinstance(categories, list):
        categories = []
    return SafetyDecision(
        risk_level=risk_level,
        categories=[str(category) for category in categories[:8]],
        action=action,
        notes=str(payload.get("notes", ""))[:500],
    )
