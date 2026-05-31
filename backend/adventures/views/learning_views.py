"""Educational MVP API views."""
from __future__ import annotations

from django.db.models import Avg, Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from rest_framework import permissions, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from .base import AdventureRunMixin
from ..models import (
    AccessibilityProfile,
    Adventure,
    BehaviorEvidence,
    ConsequenceMarker,
    AdventureHistory,
    LearnerProfile,
    LearningObjective,
    NarrativeConsequence,
    ReflectionPrompt,
    ReflectionResponse,
    RepairOpportunity,
    SafetyReview,
)
from ..serializers import (
    AccessibilityProfileSerializer,
    BehaviorEvidenceSerializer,
    ConsequenceMarkerSerializer,
    LearnerProfileSerializer,
    NarrativeConsequenceSerializer,
    RepairOpportunitySerializer,
    ReflectionPromptSerializer,
    ReflectionResponseSerializer,
    SafetyReviewSerializer,
)
from ..services.evaluation import extract_observable_evidence, save_evidence
from ..services.pedagogy import choose_reflection_prompt, get_choice_cards
from ..services.localization import localize_text
from ..utils import is_moderator


class AccessibilityProfileView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self, request):
        profile, _ = AccessibilityProfile.objects.get_or_create(user=request.user)
        return profile

    def get(self, request):
        return Response(AccessibilityProfileSerializer(self.get_object(request)).data)

    def put(self, request):
        profile = self.get_object(request)
        serializer = AccessibilityProfileSerializer(profile, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class LearnerProfileView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self, request):
        profile, _ = LearnerProfile.objects.get_or_create(user=request.user)
        return profile

    def get(self, request):
        return Response(LearnerProfileSerializer(self.get_object(request)).data)

    def put(self, request):
        profile = self.get_object(request)
        serializer = LearnerProfileSerializer(profile, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class AdventureRunLearningSummaryView(AdventureRunMixin, APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, run_id):
        adventure = self.get_adventure()
        profile, _ = AccessibilityProfile.objects.get_or_create(user=request.user)
        return Response(
            {
                "choice_cards": get_choice_cards(adventure, profile.locale)
                if profile.choice_cards_enabled
                else [],
                "can_view_teacher_dashboard": (
                    adventure.facilitator_enabled
                    and (adventure.author_user_id == request.user.id or is_moderator(request.user))
                ),
                "can_view_facilitator_dashboard": (
                    adventure.facilitator_enabled
                    and (adventure.author_user_id == request.user.id or is_moderator(request.user))
                ),
                "can_view_gm_dashboard": (
                    adventure.facilitator_enabled
                    and (adventure.author_user_id == request.user.id or is_moderator(request.user))
                ),
                "story_settings": {
                    "facilitator_enabled": adventure.facilitator_enabled,
                    "story_locale": adventure.story_locale,
                    "story_simple_language": adventure.story_simple_language,
                    "story_reduced_text_length": adventure.story_reduced_text_length,
                    "growth_analysis_enabled": adventure.growth_analysis_enabled,
                    "narrative_consequences_enabled": adventure.narrative_consequences_enabled,
                },
                "accessibility": AccessibilityProfileSerializer(profile).data,
            }
        )


class PendingReflectionView(AdventureRunMixin, APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, run_id):
        adventure = self.get_adventure()
        prompt = choose_reflection_prompt(adventure, user=request.user)
        if prompt is None:
            return Response({"prompt": None})
        data = ReflectionPromptSerializer(prompt).data
        profile, _ = AccessibilityProfile.objects.get_or_create(user=request.user)
        data["question"] = localize_text(profile.locale, data["question"])
        return Response({"prompt": data})


class ReflectionResponseCreateView(AdventureRunMixin, APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, run_id, prompt_id):
        adventure = self.get_adventure()
        prompt = ReflectionPrompt.objects.filter(
            adventure=adventure,
            id=prompt_id,
            is_active=True,
        ).first()
        if prompt is None:
            return Response({"detail": "Reflection prompt not found."}, status=status.HTTP_404_NOT_FOUND)
        content = (request.data.get("content") or "").strip()
        if not content:
            return Response({"detail": "Content is required."}, status=status.HTTP_400_BAD_REQUEST)
        history_entry_id = request.data.get("history_entry")
        if history_entry_id and not AdventureHistory.objects.filter(
            adventure=adventure,
            id=history_entry_id,
        ).exists():
            return Response(
                {"detail": "History entry not found."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        response = ReflectionResponse.objects.create(
            adventure=adventure,
            user=request.user,
            prompt=prompt,
            history_entry_id=history_entry_id or None,
            content=content,
        )
        active_competencies = set(
            LearningObjective.objects.filter(
                adventure=adventure,
                is_active=True,
            ).values_list("competency", flat=True)
        )
        if adventure.growth_analysis_enabled and active_competencies:
            evidence = [
                item
                for item in extract_observable_evidence(content)
                if item.competency in active_competencies
            ]
            save_evidence(adventure, request.user, evidence, reflection_response=response)
        return Response(ReflectionResponseSerializer(response).data, status=status.HTTP_201_CREATED)


def _ensure_teacher_access(
    view: AdventureRunMixin,
    request,
    *,
    allow_disabled: bool = False,
) -> None:
    adventure = view.get_adventure()
    if not allow_disabled and not adventure.facilitator_enabled and not is_moderator(request.user):
        raise PermissionDenied("GM layer is disabled for this run.")
    if adventure.author_user_id == request.user.id:
        return
    if is_moderator(request.user):
        return
    raise PermissionDenied("Недостаточно прав для панели GM.")


def _parse_bool(value) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)


class TeacherDashboardView(AdventureRunMixin, APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_adventure(self) -> Adventure:
        if not hasattr(self, "_adventure"):
            adventure = get_object_or_404(
                Adventure,
                id=self.kwargs["run_id"],
                is_template=False,
            )
            if adventure.author_user_id != self.request.user.id and not is_moderator(
                self.request.user
            ):
                raise PermissionDenied("Недостаточно прав для панели GM.")
            self._adventure = adventure
        return self._adventure

    def get(self, request, run_id):
        _ensure_teacher_access(self, request)
        adventure = self.get_adventure()
        evidence = BehaviorEvidence.objects.filter(adventure=adventure).select_related("user")
        reflections = ReflectionResponse.objects.filter(adventure=adventure)
        safety = SafetyReview.objects.filter(adventure=adventure)
        repair_opportunities = RepairOpportunity.objects.filter(adventure=adventure)
        consequence_markers = ConsequenceMarker.objects.filter(adventure=adventure)
        narrative_consequences = NarrativeConsequence.objects.filter(adventure=adventure)
        competency_summary = (
            evidence.values("competency")
            .annotate(avg_score=Avg("score"), count=Count("id"))
            .order_by("competency")
        )
        return Response(
            {
                "story_settings": {
                    "facilitator_enabled": adventure.facilitator_enabled,
                    "story_locale": adventure.story_locale,
                    "story_simple_language": adventure.story_simple_language,
                    "story_reduced_text_length": adventure.story_reduced_text_length,
                    "growth_analysis_enabled": adventure.growth_analysis_enabled,
                    "narrative_consequences_enabled": adventure.narrative_consequences_enabled,
                },
                "competencies": list(competency_summary),
                "latest_evidence": BehaviorEvidenceSerializer(
                    evidence.order_by("-created_at")[:30],
                    many=True,
                ).data,
                "open_repair_opportunities": RepairOpportunitySerializer(
                    repair_opportunities.filter(
                        status__in=[
                            RepairOpportunity.Status.OPEN,
                            RepairOpportunity.Status.IN_PROGRESS,
                        ]
                    ).order_by("-created_at")[:30],
                    many=True,
                ).data,
                "latest_consequence_markers": ConsequenceMarkerSerializer(
                    consequence_markers.order_by("-created_at")[:30],
                    many=True,
                ).data,
                "latest_narrative_consequences": NarrativeConsequenceSerializer(
                    narrative_consequences.prefetch_related(
                        "character_links",
                        "location_links",
                        "faction_links",
                    ).order_by("-updated_at")[:30],
                    many=True,
                ).data,
                "reflection_completion": {
                    "responses": reflections.count(),
                    "active_prompts": ReflectionPrompt.objects.filter(
                        adventure=adventure,
                        is_active=True,
                    ).count(),
                    "learners": reflections.values("user").distinct().count(),
                },
                "safety_incidents": SafetyReviewSerializer(
                    safety.filter(Q(action="warn") | Q(action="block")).order_by("-created_at")[:20],
                    many=True,
                ).data,
            }
        )

    def put(self, request, run_id):
        _ensure_teacher_access(self, request, allow_disabled=True)
        adventure = self.get_adventure()
        allowed_fields = (
            "facilitator_enabled",
            "story_simple_language",
            "story_reduced_text_length",
            "growth_analysis_enabled",
            "narrative_consequences_enabled",
        )
        update_fields = []
        for field in allowed_fields:
            if field in request.data:
                setattr(adventure, field, _parse_bool(request.data[field]))
                update_fields.append(field)
        if "story_locale" in request.data:
            story_locale = request.data["story_locale"]
            if story_locale not in Adventure.StoryLocale.values:
                return Response(
                    {"detail": "Unsupported story locale."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            adventure.story_locale = story_locale
            update_fields.append("story_locale")
        if update_fields:
            adventure.save(update_fields=update_fields + ["updated_at"])
        return Response(
            {
                "story_settings": {
                    "facilitator_enabled": adventure.facilitator_enabled,
                    "story_locale": adventure.story_locale,
                    "story_simple_language": adventure.story_simple_language,
                    "story_reduced_text_length": adventure.story_reduced_text_length,
                    "growth_analysis_enabled": adventure.growth_analysis_enabled,
                    "narrative_consequences_enabled": adventure.narrative_consequences_enabled,
                }
            }
        )


class PortfolioExportView(AdventureRunMixin, APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_adventure(self) -> Adventure:
        if not hasattr(self, "_adventure"):
            adventure = get_object_or_404(
                Adventure,
                id=self.kwargs["run_id"],
                is_template=False,
            )
            if (
                not self._has_run_access(adventure)
                and adventure.author_user_id != self.request.user.id
                and not is_moderator(self.request.user)
            ):
                raise PermissionDenied("Недостаточно прав для экспорта portfolio.")
            self._adventure = adventure
        return self._adventure

    def get(self, request, run_id):
        adventure = self.get_adventure()
        can_export_run = adventure.author_user_id == request.user.id or is_moderator(request.user)
        evidence = BehaviorEvidence.objects.filter(adventure=adventure)
        reflections = ReflectionResponse.objects.filter(adventure=adventure)
        repair_opportunities = RepairOpportunity.objects.filter(adventure=adventure)
        consequence_markers = ConsequenceMarker.objects.filter(adventure=adventure)
        narrative_consequences = NarrativeConsequence.objects.filter(adventure=adventure)
        if not can_export_run:
            evidence = evidence.filter(user=request.user)
            reflections = reflections.filter(user=request.user)
            repair_opportunities = repair_opportunities.filter(user=request.user)
            consequence_markers = consequence_markers.filter(user=request.user)
        payload = {
            "adventure": {"id": adventure.id, "title": adventure.title},
            "scope": "run" if can_export_run else "learner",
            "learner_count": reflections.values("user").distinct().count()
            if can_export_run
            else 1,
            "competencies": list(
                evidence.values("competency")
                .annotate(avg_score=Avg("score"), count=Count("id"))
                .order_by("competency")
            ),
            "evidence": BehaviorEvidenceSerializer(evidence.order_by("-created_at"), many=True).data,
            "repair_opportunities": RepairOpportunitySerializer(
                repair_opportunities.order_by("-created_at"),
                many=True,
            ).data,
            "consequence_markers": ConsequenceMarkerSerializer(
                consequence_markers.order_by("-created_at"),
                many=True,
            ).data,
            "narrative_consequences": NarrativeConsequenceSerializer(
                narrative_consequences.prefetch_related(
                    "character_links",
                    "location_links",
                    "faction_links",
                ).order_by("-updated_at"),
                many=True,
            ).data
            if can_export_run
            else [],
            "reflections": ReflectionResponseSerializer(reflections.order_by("-created_at"), many=True).data,
        }
        return JsonResponse(payload, json_dumps_params={"ensure_ascii": False, "indent": 2})
