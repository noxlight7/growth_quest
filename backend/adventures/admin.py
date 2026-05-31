"""Admin registration for adventure and educational MVP models."""
from django.contrib import admin

from .models import (
    AccessibilityProfile,
    BehaviorEvidence,
    ConsequenceMarker,
    LearnerProfile,
    LearningObjective,
    NarrativeConsequence,
    NarrativeConsequenceCharacter,
    NarrativeConsequenceFaction,
    NarrativeConsequenceLocation,
    PedagogicalIntervention,
    RepairOpportunity,
    ReflectionPrompt,
    ReflectionResponse,
    SafetyReview,
    TurnAnalysisLog,
)


admin.site.register(AccessibilityProfile)
admin.site.register(LearnerProfile)
admin.site.register(LearningObjective)
admin.site.register(ReflectionPrompt)
admin.site.register(ReflectionResponse)
admin.site.register(BehaviorEvidence)
admin.site.register(RepairOpportunity)
admin.site.register(ConsequenceMarker)
admin.site.register(NarrativeConsequence)
admin.site.register(NarrativeConsequenceCharacter)
admin.site.register(NarrativeConsequenceLocation)
admin.site.register(NarrativeConsequenceFaction)
admin.site.register(PedagogicalIntervention)
admin.site.register(SafetyReview)
admin.site.register(TurnAnalysisLog)
