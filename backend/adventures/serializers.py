"""
Serializers for the adventures app.
"""
from __future__ import annotations

from rest_framework import serializers

from .models import (
    Adventure,
    AdventureHeroSetup,
    AdventurePlayer,
    AccessibilityProfile,
    BehaviorEvidence,
    ConsequenceMarker,
    ModerationEntry,
    PublishedAdventure,
    Character,
    CharacterSystem,
    CharacterTechnique,
    AdventureEvent,
    Faction,
    AdventureHistory,
    LearnerProfile,
    LearningObjective,
    Location,
    NarrativeConsequence,
    OtherInfo,
    PedagogicalIntervention,
    Race,
    RepairOpportunity,
    ReflectionPrompt,
    ReflectionResponse,
    SafetyReview,
    SkillSystem,
    Technique,
)


class AdventureTemplateSerializer(serializers.ModelSerializer):
    """Serializer for listing/creating adventure templates."""

    is_under_moderation = serializers.SerializerMethodField()
    is_published = serializers.SerializerMethodField()
    can_edit = serializers.SerializerMethodField()
    author_username = serializers.CharField(source="author_user.username", read_only=True)
    primary_heroes = serializers.PrimaryKeyRelatedField(
        many=True,
        required=False,
        queryset=Character.objects.all(),
    )

    class Meta:
        model = Adventure
        fields = (
            "id",
            "title",
            "description",
            "spec_instructions",
            "intro",
            "story_locale",
            "facilitator_enabled",
            "story_simple_language",
            "story_reduced_text_length",
            "growth_analysis_enabled",
            "narrative_consequences_enabled",
            "primary_heroes",
            "created_at",
            "updated_at",
            "is_under_moderation",
            "is_published",
            "can_edit",
            "author_username",
        )
        read_only_fields = (
            "id",
            "created_at",
            "updated_at",
            "is_under_moderation",
            "is_published",
            "can_edit",
            "author_username",
        )

    def create(self, validated_data: dict) -> Adventure:
        user = self.context["request"].user
        primary_heroes = validated_data.pop("primary_heroes", [])
        adventure = Adventure.objects.create(
            author_user=user,
            is_template=True,
            player_user=None,
            template_adventure=None,
            **validated_data,
        )
        if primary_heroes:
            adventure.primary_heroes.set(primary_heroes)
        return adventure

    def validate(self, attrs: dict) -> dict:
        adventure = self.instance
        primary_heroes = attrs.get(
            "primary_heroes",
            list(adventure.primary_heroes.all()) if adventure else None,
        )
        if adventure is None and primary_heroes:
            raise serializers.ValidationError(
                {"primary_heroes": "Главных героев можно назначить после создания приключения."}
            )
        if adventure and primary_heroes:
            invalid = [
                hero for hero in primary_heroes if hero.adventure_id != adventure.id
            ]
            if invalid:
                raise serializers.ValidationError(
                    {"primary_heroes": "Главные герои принадлежат другому приключению."}
                )
            if len(primary_heroes) > adventure.max_players:
                raise serializers.ValidationError(
                    {"primary_heroes": "Слишком много главных героев."}
                )
        return attrs

    def get_is_under_moderation(self, obj: Adventure) -> bool:
        try:
            obj.moderation_entry
            return True
        except ModerationEntry.DoesNotExist:
            return False

    def get_is_published(self, obj: Adventure) -> bool:
        try:
            obj.publication_entry
            return True
        except PublishedAdventure.DoesNotExist:
            return False

    def get_can_edit(self, obj: Adventure) -> bool:
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return False
        return obj.author_user_id == request.user.id


class ModerationEntrySerializer(serializers.ModelSerializer):
    adventure_id = serializers.IntegerField(source="adventure.id", read_only=True)
    title = serializers.CharField(source="adventure.title", read_only=True)
    author_username = serializers.CharField(source="adventure.author_user.username", read_only=True)

    class Meta:
        model = ModerationEntry
        fields = ("adventure_id", "title", "author_username", "submitted_at")


class PublishedAdventureSerializer(serializers.ModelSerializer):
    adventure_id = serializers.IntegerField(source="adventure.id", read_only=True)
    title = serializers.CharField(source="adventure.title", read_only=True)
    description = serializers.CharField(source="adventure.description", read_only=True)
    author_username = serializers.CharField(source="adventure.author_user.username", read_only=True)

    class Meta:
        model = PublishedAdventure
        fields = ("adventure_id", "title", "description", "author_username", "published_at")


class AdventureHeroSetupSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdventureHeroSetup
        fields = (
            "default_location",
            "require_race",
            "default_race",
            "require_age",
            "default_age",
            "require_body_power",
            "default_body_power",
            "require_mind_power",
            "default_mind_power",
            "require_will_power",
            "default_will_power",
            "require_systems",
            "require_techniques",
        )

    def validate_default_race(self, value):
        if value is None:
            return value
        if self.instance and value.adventure_id != self.instance.adventure_id:
            raise serializers.ValidationError("Раса принадлежит другому приключению.")
        return value

    def validate_default_location(self, value):
        if value is None:
            return value
        if self.instance and value.adventure_id != self.instance.adventure_id:
            raise serializers.ValidationError("Локация принадлежит другому приключению.")
        return value


class AdventureRunSerializer(serializers.ModelSerializer):
    primary_heroes = serializers.PrimaryKeyRelatedField(many=True, read_only=True)

    class Meta:
        model = Adventure
        fields = (
            "id",
            "title",
            "description",
            "intro",
            "spec_instructions",
            "story_locale",
            "facilitator_enabled",
            "story_simple_language",
            "story_reduced_text_length",
            "growth_analysis_enabled",
            "narrative_consequences_enabled",
            "template_adventure",
            "primary_heroes",
            "shared_location",
            "max_players",
            "rollback_min_history_id",
            "started_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class AdventureRunDetailSerializer(serializers.ModelSerializer):
    primary_heroes = serializers.PrimaryKeyRelatedField(
        many=True,
        required=False,
        queryset=Character.objects.all(),
    )

    class Meta:
        model = Adventure
        fields = (
            "id",
            "title",
            "description",
            "intro",
            "spec_instructions",
            "story_locale",
            "facilitator_enabled",
            "story_simple_language",
            "story_reduced_text_length",
            "growth_analysis_enabled",
            "narrative_consequences_enabled",
            "template_adventure",
            "primary_heroes",
            "shared_location",
            "max_players",
            "rollback_min_history_id",
            "started_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "template_adventure",
            "shared_location",
            "max_players",
            "started_at",
            "created_at",
            "updated_at",
        )

    def validate(self, attrs: dict) -> dict:
        adventure = self.instance
        primary_heroes = attrs.get(
            "primary_heroes",
            list(adventure.primary_heroes.all()) if adventure else None,
        )
        if adventure and primary_heroes:
            invalid = [
                hero for hero in primary_heroes if hero.adventure_id != adventure.id
            ]
            if invalid:
                raise serializers.ValidationError(
                    {"primary_heroes": "Главные герои принадлежат другому приключению."}
                )
            if len(primary_heroes) > adventure.max_players:
                raise serializers.ValidationError(
                    {"primary_heroes": "Слишком много главных героев."}
                )
        return attrs


class AdventurePlayerSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(source="user.id", read_only=True, allow_null=True)
    username = serializers.CharField(source="user.username", read_only=True, allow_null=True)
    hero_id = serializers.IntegerField(source="hero.id", read_only=True)
    hero_title = serializers.CharField(source="hero.title", read_only=True)

    class Meta:
        model = AdventurePlayer
        fields = (
            "slot_number",
            "user_id",
            "username",
            "hero_id",
            "hero_title",
            "is_npc",
            "wrote_after_ai",
        )


class LocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Location
        fields = (
            "id",
            "title",
            "description",
            "x",
            "y",
            "width",
            "height",
            "tags",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")


class RaceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Race
        fields = (
            "id",
            "title",
            "description",
            "life_span",
            "tags",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")


class SkillSystemSerializer(serializers.ModelSerializer):
    class Meta:
        model = SkillSystem
        fields = (
            "id",
            "title",
            "description",
            "tags",
            "w_body",
            "w_mind",
            "w_will",
            "formula_hint",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")

    def validate(self, attrs: dict) -> dict:
        w_body = attrs.get("w_body", getattr(self.instance, "w_body", 0))
        w_mind = attrs.get("w_mind", getattr(self.instance, "w_mind", 0))
        w_will = attrs.get("w_will", getattr(self.instance, "w_will", 0))
        if w_body < 0 or w_mind < 0 or w_will < 0:
            raise serializers.ValidationError("Веса характеристик не могут быть отрицательными.")
        if (w_body + w_mind + w_will) <= 0:
            raise serializers.ValidationError("Нужно задать хотя бы один вес больше нуля.")
        return attrs


class TechniqueSerializer(serializers.ModelSerializer):
    class Meta:
        model = Technique
        fields = (
            "id",
            "system",
            "title",
            "description",
            "tags",
            "difficulty",
            "tier",
            "required_system_level",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")

    def validate(self, attrs: dict) -> dict:
        adventure = self.context.get("adventure")
        if adventure is None:
            return attrs
        system = attrs.get("system", getattr(self.instance, "system", None))
        if system and system.adventure_id != adventure.id:
            raise serializers.ValidationError({"system": "Система из другого приключения."})
        return attrs


class FactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Faction
        fields = ("id", "title", "description", "tags", "created_at", "updated_at")
        read_only_fields = ("id", "created_at", "updated_at")


class OtherInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = OtherInfo
        fields = (
            "id",
            "category",
            "title",
            "description",
            "tags",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")

class CharacterSerializer(serializers.ModelSerializer):
    player_username = serializers.SerializerMethodField()

    class Meta:
        model = Character
        fields = (
            "id",
            "title",
            "description",
            "is_player",
            "in_party",
            "story_status",
            "player_username",
            "age",
            "body_power",
            "body_power_progress",
            "mind_power",
            "mind_power_progress",
            "will_power",
            "will_power_progress",
            "race",
            "location",
            "tags",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")

    def get_player_username(self, obj: Character) -> str | None:
        if hasattr(obj, "_prefetched_objects_cache") and "player_slots" in obj._prefetched_objects_cache:
            for slot in obj.player_slots.all():
                if not slot.is_npc and slot.user_id:
                    return slot.user.username if slot.user else None
            return None
        slot = (
            obj.player_slots.filter(is_npc=False, user__isnull=False)
            .select_related("user")
            .first()
        )
        return slot.user.username if slot and slot.user else None

    def validate(self, attrs: dict) -> dict:
        adventure = self.context.get("adventure")
        if adventure is None:
            return attrs
        race = attrs.get("race", getattr(self.instance, "race", None))
        if race and race.adventure_id != adventure.id:
            raise serializers.ValidationError({"race": "Раса принадлежит другому приключению."})
        location = attrs.get("location", getattr(self.instance, "location", None))
        if location and location.adventure_id != adventure.id:
            raise serializers.ValidationError({"location": "Локация принадлежит другому приключению."})
        for field in (
            "body_power_progress",
            "mind_power_progress",
            "will_power_progress",
        ):
            value = attrs.get(field, getattr(self.instance, field, 0))
            if value < 0 or value > 100:
                raise serializers.ValidationError({field: "Прогресс должен быть в диапазоне 0-100."})
        return attrs


class CharacterSystemSerializer(serializers.ModelSerializer):
    class Meta:
        model = CharacterSystem
        fields = (
            "id",
            "character",
            "system",
            "level",
            "progress_percent",
            "notes",
        )
        read_only_fields = ("id",)

    def validate(self, attrs: dict) -> dict:
        adventure = self.context.get("adventure")
        if adventure is None:
            return attrs
        character = attrs.get("character", getattr(self.instance, "character", None))
        if character and character.adventure_id != adventure.id:
            raise serializers.ValidationError({"character": "Персонаж из другого приключения."})
        system = attrs.get("system", getattr(self.instance, "system", None))
        if system and system.adventure_id != adventure.id:
            raise serializers.ValidationError({"system": "Система из другого приключения."})
        if character and system and character.adventure_id != system.adventure_id:
            raise serializers.ValidationError({"system": "Система из другого приключения."})
        progress = attrs.get("progress_percent", getattr(self.instance, "progress_percent", 0))
        if progress < 0 or progress > 100:
            raise serializers.ValidationError(
                {"progress_percent": "Прогресс должен быть в диапазоне 0-100."}
            )
        return attrs


class CharacterTechniqueSerializer(serializers.ModelSerializer):
    class Meta:
        model = CharacterTechnique
        fields = (
            "id",
            "character",
            "technique",
            "learned_at",
            "notes",
        )
        read_only_fields = ("id", "learned_at")

    def validate(self, attrs: dict) -> dict:
        adventure = self.context.get("adventure")
        if adventure is None:
            return attrs
        character = attrs.get("character", getattr(self.instance, "character", None))
        if character and character.adventure_id != adventure.id:
            raise serializers.ValidationError({"character": "Персонаж из другого приключения."})
        technique = attrs.get("technique", getattr(self.instance, "technique", None))
        if technique and technique.system.adventure_id != adventure.id:
            raise serializers.ValidationError({"technique": "Прием из другого приключения."})
        if character and technique and character.adventure_id != technique.system.adventure_id:
            raise serializers.ValidationError({"technique": "Прием из другого приключения."})
        return attrs


class AdventureEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdventureEvent
        fields = (
            "id",
            "location",
            "status",
            "title",
            "trigger_hint",
            "state",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")

    def validate(self, attrs: dict) -> dict:
        adventure = self.context.get("adventure")
        if adventure is None:
            return attrs
        location = attrs.get("location", getattr(self.instance, "location", None))
        if location and location.adventure_id != adventure.id:
            raise serializers.ValidationError({"location": "Локация из другого приключения."})
        return attrs


class AdventureHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = AdventureHistory
        fields = ("id", "role", "content", "metadata", "created_at")
        read_only_fields = ("id", "created_at")


class AccessibilityProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = AccessibilityProfile
        fields = (
            "locale",
            "simple_language",
            "high_contrast",
            "reduced_text_length",
            "choice_cards_enabled",
            "content_warnings_enabled",
            "updated_at",
        )
        read_only_fields = ("updated_at",)


class LearnerProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = LearnerProfile
        fields = ("age_band", "consent_confirmed", "notes", "updated_at")
        read_only_fields = ("updated_at",)


class LearningObjectiveSerializer(serializers.ModelSerializer):
    class Meta:
        model = LearningObjective
        fields = (
            "id",
            "code",
            "title",
            "description",
            "competency",
            "weight",
            "is_active",
        )
        read_only_fields = ("id",)


class ReflectionPromptSerializer(serializers.ModelSerializer):
    objective = serializers.PrimaryKeyRelatedField(queryset=LearningObjective.objects.all())
    objective_detail = LearningObjectiveSerializer(source="objective", read_only=True)

    class Meta:
        model = ReflectionPrompt
        fields = ("id", "objective", "objective_detail", "trigger_kind", "question", "is_active")
        read_only_fields = ("id", "objective_detail")

    def validate_objective(self, objective):
        adventure = self.context.get("adventure")
        if adventure is not None and objective.adventure_id != adventure.id:
            raise serializers.ValidationError("Objective belongs to another adventure.")
        return objective

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["objective"] = LearningObjectiveSerializer(instance.objective).data
        return data


class ReflectionResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReflectionResponse
        fields = ("id", "prompt", "history_entry", "content", "created_at")
        read_only_fields = ("id", "created_at")


class BehaviorEvidenceSerializer(serializers.ModelSerializer):
    source = serializers.SerializerMethodField()

    class Meta:
        model = BehaviorEvidence
        fields = (
            "id",
            "history_entry",
            "reflection_response",
            "competency",
            "marker",
            "score",
            "confidence",
            "excerpt",
            "rationale",
            "source",
            "created_at",
        )
        read_only_fields = fields

    def get_source(self, obj: BehaviorEvidence) -> str:
        if obj.reflection_response_id:
            return "reflection"
        if obj.history_entry_id:
            return "history"
        return "manual"


class RepairOpportunitySerializer(serializers.ModelSerializer):
    class Meta:
        model = RepairOpportunity
        fields = (
            "id",
            "source_history_entry",
            "source_evidence",
            "related_event",
            "competency",
            "status",
            "title",
            "description",
            "suggested_action",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class ConsequenceMarkerSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConsequenceMarker
        fields = (
            "id",
            "history_entry",
            "evidence",
            "competency",
            "kind",
            "title",
            "description",
            "weight",
            "tags",
            "created_at",
        )
        read_only_fields = fields


class NarrativeConsequenceSerializer(serializers.ModelSerializer):
    characters = serializers.SerializerMethodField()
    locations = serializers.SerializerMethodField()
    factions = serializers.SerializerMethodField()

    class Meta:
        model = NarrativeConsequence
        fields = (
            "id",
            "source_history_entry",
            "title",
            "summary",
            "status",
            "certainty",
            "importance",
            "characters",
            "locations",
            "factions",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields

    def get_characters(self, obj: NarrativeConsequence) -> list[int]:
        return [link.character_id for link in obj.character_links.all()]

    def get_locations(self, obj: NarrativeConsequence) -> list[int]:
        return [link.location_id for link in obj.location_links.all()]

    def get_factions(self, obj: NarrativeConsequence) -> list[int]:
        return [link.faction_id for link in obj.faction_links.all()]


class PedagogicalInterventionSerializer(serializers.ModelSerializer):
    objective_detail = LearningObjectiveSerializer(source="objective", read_only=True)

    class Meta:
        model = PedagogicalIntervention
        fields = ("id", "objective", "objective_detail", "kind", "payload", "is_active")
        read_only_fields = ("id", "objective_detail")

    def validate_objective(self, objective):
        adventure = self.context.get("adventure")
        if adventure is not None and objective.adventure_id != adventure.id:
            raise serializers.ValidationError("Objective belongs to another adventure.")
        return objective


class SafetyReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = SafetyReview
        fields = (
            "id",
            "history_entry",
            "source",
            "risk_level",
            "categories",
            "action",
            "notes",
            "created_at",
        )
        read_only_fields = fields
