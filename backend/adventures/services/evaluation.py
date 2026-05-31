"""LLM-backed observable gameplay evidence extraction and persistence."""
from __future__ import annotations

from collections.abc import Iterable

from django.contrib.auth import get_user_model

from backend.llm import LLMClient, get_llm_client

from ..models import Adventure, AdventureHistory, BehaviorEvidence, ReflectionResponse
from ..schemas.llm import EvidenceItem, parse_evaluator_output


ALLOWED_COMPETENCIES = {
    "empathy",
    "cooperation",
    "self_regulation",
    "responsible_decision",
    "restorative_action",
    "help_seeking",
    "inclusion",
}


def _dedupe_evidence(items: Iterable[EvidenceItem]) -> list[EvidenceItem]:
    deduped: list[EvidenceItem] = []
    seen = set()
    for item in items:
        key = (
            item.competency,
            item.marker,
            item.score,
            item.excerpt.strip().lower()[:120],
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


def extract_evidence_from_json(raw_text: str) -> list[EvidenceItem]:
    return parse_evaluator_output(raw_text)


def _build_evaluator_prompt(text: str) -> str:
    competencies = ", ".join(sorted(ALLOWED_COMPETENCIES))
    return (
        "Evaluate this player-authored narrative-game text for observable growth evidence.\n"
        "Return only valid JSON, no markdown, no commentary.\n"
        "Schema: {\"evidence\":[{\"competency\":\"...\",\"marker\":\"...\","
        "\"score\":-2,\"confidence\":0.0,\"excerpt\":\"exact quote from text\","
        "\"rationale\":\"observable reason\"}]}\n"
        f"Allowed competencies: {competencies}.\n"
        "Rules:\n"
        "- Include only observable choices, actions, requests, or explicit hero-state text.\n"
        "- Do not infer personality, diagnosis, hidden intent, or unstated emotion.\n"
        "- Use setting-appropriate wording. The text may come from fantasy, science fiction, "
        "historical fiction, or a contemporary scenario.\n"
        "- Omit ambiguous evidence. Empty evidence is a valid result.\n"
        "- The excerpt must be copied from the player text and support the marker directly.\n"
        "- Use positive score for a demonstrated constructive strategy and negative score only "
        "for a concrete growth or repair opportunity visible in the action.\n\n"
        f"Player text:\n{text[:2500]}"
    )


def _excerpt_is_supported(text: str, excerpt: str) -> bool:
    cleaned_excerpt = (excerpt or "").strip()
    if not cleaned_excerpt:
        return False
    return cleaned_excerpt.lower() in text.lower()


def _passes_quality_checks(item: EvidenceItem, text: str) -> bool:
    if item.competency not in ALLOWED_COMPETENCIES:
        return False
    if not item.marker or len(item.marker) > 128:
        return False
    if item.confidence < 0.55:
        return False
    return _excerpt_is_supported(text, item.excerpt)


def extract_llm_evidence(
    text: str,
    *,
    client: LLMClient | None = None,
) -> list[EvidenceItem]:
    llm_client = client or get_llm_client()
    response = llm_client.generate(
        prompt=_build_evaluator_prompt(text),
        system=(
            "You extract observable evidence from a narrative game. "
            "You never produce hidden personality profiles or unsupported claims."
        ),
        max_tokens=650,
        temperature=0.0,
    )
    items = extract_evidence_from_json(response.text)
    return _dedupe_evidence([item for item in items if _passes_quality_checks(item, text)])


def extract_observable_evidence(
    text: str,
    *,
    client: LLMClient | None = None,
    mode: str | None = None,
) -> list[EvidenceItem]:
    """Extract evidence with an empty fallback when the configured model is unavailable."""
    if mode == "disabled":
        return []
    try:
        return extract_llm_evidence(text, client=client)
    except Exception:
        return []


def save_evidence(
    adventure: Adventure,
    user: get_user_model(),
    items: Iterable[EvidenceItem],
    *,
    history_entry: AdventureHistory | None = None,
    reflection_response: ReflectionResponse | None = None,
) -> list[BehaviorEvidence]:
    created: list[BehaviorEvidence] = []
    for item in items:
        if item.competency not in ALLOWED_COMPETENCIES:
            continue
        created.append(
            BehaviorEvidence.objects.create(
                adventure=adventure,
                user=user,
                history_entry=history_entry,
                reflection_response=reflection_response,
                competency=item.competency,
                marker=item.marker[:128],
                score=max(-2, min(2, item.score)),
                confidence=max(0.0, min(1.0, item.confidence)),
                excerpt=item.excerpt[:500],
                rationale=item.rationale[:500],
            )
        )
    return created
