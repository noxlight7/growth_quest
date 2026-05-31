"""Domain models for adventures, entities, and gameplay history."""
from __future__ import annotations

from django.conf import settings
from django.contrib.postgres.fields import ArrayField
from django.contrib.postgres.indexes import GinIndex
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Q


class Adventure(models.Model):
    class StoryLocale(models.TextChoices):
        RU = "ru", "ru"
        EN = "en", "en"
        ZH_CN = "zh-CN", "zh-CN"

    is_template = models.BooleanField(default=False)
    is_waiting_ai = models.BooleanField(default=False)
    rollback_min_history_id = models.BigIntegerField(null=True, blank=True)
    author_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.RESTRICT,
        related_name="authored_adventures",
    )
    player_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="played_adventures",
    )
    template_adventure = models.ForeignKey(
        "self",
        on_delete=models.RESTRICT,
        null=True,
        blank=True,
        related_name="runs",
    )
    primary_hero = models.ForeignKey(
        "Character",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="primary_in_adventures",
    )
    primary_heroes = models.ManyToManyField(
        "Character",
        blank=True,
        related_name="primary_in_multi_adventures",
    )
    shared_location = models.ForeignKey(
        "Location",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="shared_in_adventures",
    )
    max_players = models.PositiveSmallIntegerField(default=5)
    invite_token = models.CharField(max_length=64, unique=True, null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    title = models.TextField()
    description = models.TextField(blank=True)
    intro = models.TextField(blank=True)
    spec_instructions = models.TextField(blank=True)
    story_locale = models.CharField(max_length=8, choices=StoryLocale.choices, default=StoryLocale.EN)
    facilitator_enabled = models.BooleanField(default=True)
    story_simple_language = models.BooleanField(default=False)
    story_reduced_text_length = models.BooleanField(default=False)
    growth_analysis_enabled = models.BooleanField(default=False)
    narrative_consequences_enabled = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                name="adventures_template_or_run_chk",
                condition=(
                    (
                        Q(is_template=True)
                        & Q(player_user__isnull=True)
                        & Q(template_adventure__isnull=True)
                    )
                    | (
                        Q(is_template=False)
                        & Q(player_user__isnull=False)
                        & Q(template_adventure__isnull=False)
                    )
                ),
            ),
        ]
        indexes = [
            models.Index(
                fields=["player_user"],
                name="idx_adventures_player",
                condition=Q(is_template=False),
            ),
            models.Index(fields=["is_template"], name="idx_adventures_template"),
        ]

    def __str__(self) -> str:
        return self.title

    def clean(self) -> None:
        if self.primary_hero_id and self.id and self.primary_hero.adventure_id != self.id:
            raise ValidationError("Primary hero adventure mismatch.")
        if self.shared_location_id and self.id and self.shared_location.adventure_id != self.id:
            raise ValidationError("Shared location adventure mismatch.")


class AdventurePlayer(models.Model):
    adventure = models.ForeignKey(Adventure, on_delete=models.CASCADE, related_name="players")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="adventure_memberships",
        null=True,
        blank=True,
    )
    hero = models.ForeignKey(
        "Character",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="player_slots",
    )
    slot_number = models.PositiveSmallIntegerField()
    is_npc = models.BooleanField(default=False)
    wrote_after_ai = models.BooleanField(default=False)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["adventure", "user"],
                name="uq_adventure_player_user",
            ),
            models.UniqueConstraint(
                fields=["adventure", "slot_number"],
                name="uq_adventure_player_slot",
            ),
            models.UniqueConstraint(
                fields=["adventure", "hero"],
                name="uq_adventure_player_hero",
                condition=Q(hero__isnull=False),
            ),
            models.CheckConstraint(
                name="adventure_player_user_or_npc_chk",
                condition=(
                    (Q(is_npc=False) & Q(user__isnull=False))
                    | (Q(is_npc=True) & Q(user__isnull=True))
                ),
            ),
        ]

    def clean(self) -> None:
        if self.hero_id and self.adventure_id and self.hero.adventure_id != self.adventure_id:
            raise ValidationError("Hero adventure mismatch.")


class AdventureHeroSetup(models.Model):
    adventure = models.OneToOneField(
        Adventure,
        on_delete=models.CASCADE,
        related_name="hero_setup",
    )
    default_location = models.ForeignKey(
        "Location",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="default_for_hero_setup",
    )
    require_race = models.BooleanField(default=True)
    default_race = models.ForeignKey(
        "Race",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="default_for_hero_setup",
    )
    require_age = models.BooleanField(default=False)
    default_age = models.IntegerField(null=True, blank=True)
    require_body_power = models.BooleanField(default=True)
    default_body_power = models.IntegerField(null=True, blank=True)
    require_mind_power = models.BooleanField(default=True)
    default_mind_power = models.IntegerField(null=True, blank=True)
    require_will_power = models.BooleanField(default=True)
    default_will_power = models.IntegerField(null=True, blank=True)
    require_systems = models.BooleanField(default=False)
    require_techniques = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.CheckConstraint(
                name="hero_setup_default_age_nonneg",
                condition=Q(default_age__gte=0) | Q(default_age__isnull=True),
            ),
            models.CheckConstraint(
                name="hero_setup_default_body_nonneg",
                condition=Q(default_body_power__gte=0) | Q(default_body_power__isnull=True),
            ),
            models.CheckConstraint(
                name="hero_setup_default_mind_nonneg",
                condition=Q(default_mind_power__gte=0) | Q(default_mind_power__isnull=True),
            ),
            models.CheckConstraint(
                name="hero_setup_default_will_nonneg",
                condition=Q(default_will_power__gte=0) | Q(default_will_power__isnull=True),
            ),
        ]
        indexes = [
            models.Index(fields=["adventure"], name="idx_hero_setup_adv"),
        ]


class Location(models.Model):
    adventure = models.ForeignKey(Adventure, on_delete=models.CASCADE, related_name="locations")
    title = models.TextField()
    description = models.TextField(blank=True)
    x = models.IntegerField(default=0)
    y = models.IntegerField(default=0)
    width = models.IntegerField(default=1)
    height = models.IntegerField(default=1)
    tags = ArrayField(models.TextField(), default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(name="locations_width_gt_zero", condition=Q(width__gt=0)),
            models.CheckConstraint(name="locations_height_gt_zero", condition=Q(height__gt=0)),
        ]
        indexes = [
            models.Index(fields=["adventure", "x", "y"], name="idx_locations_adv_xy"),
            GinIndex(fields=["tags"], name="idx_locations_tags_gin"),
        ]

    def __str__(self) -> str:
        return self.title


class Race(models.Model):
    adventure = models.ForeignKey(Adventure, on_delete=models.CASCADE, related_name="races")
    title = models.TextField()
    description = models.TextField(blank=True)
    life_span = models.IntegerField(default=100)
    tags = ArrayField(models.TextField(), default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [GinIndex(fields=["tags"], name="idx_races_tags_gin")]

    def __str__(self) -> str:
        return self.title


class Character(models.Model):
    class StoryStatus(models.TextChoices):
        ACTIVE = "active", "active"
        DEAD = "dead", "dead"
        MISSING = "missing", "missing"
        INACTIVE = "inactive", "inactive"

    adventure = models.ForeignKey(Adventure, on_delete=models.CASCADE, related_name="characters")
    race = models.ForeignKey(
        Race,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="characters",
    )
    location = models.ForeignKey(
        Location,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="characters",
    )
    is_player = models.BooleanField(default=False)
    in_party = models.BooleanField(default=False)
    story_status = models.CharField(
        max_length=16,
        choices=StoryStatus.choices,
        default=StoryStatus.ACTIVE,
    )
    title = models.TextField()
    age = models.IntegerField(null=True, blank=True)
    body_power = models.IntegerField(default=0)
    body_power_progress = models.IntegerField(default=0)
    mind_power = models.IntegerField(default=0)
    mind_power_progress = models.IntegerField(default=0)
    will_power = models.IntegerField(default=0)
    will_power_progress = models.IntegerField(default=0)
    description = models.TextField(blank=True)
    tags = ArrayField(models.TextField(), default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                name="characters_age_non_negative",
                condition=Q(age__gte=0) | Q(age__isnull=True),
            ),
            models.CheckConstraint(
                name="characters_body_non_negative",
                condition=Q(body_power__gte=0),
            ),
            models.CheckConstraint(
                name="characters_body_progress_range",
                condition=Q(body_power_progress__gte=0) & Q(body_power_progress__lte=100),
            ),
            models.CheckConstraint(
                name="characters_mind_non_negative",
                condition=Q(mind_power__gte=0),
            ),
            models.CheckConstraint(
                name="characters_mind_progress_range",
                condition=Q(mind_power_progress__gte=0) & Q(mind_power_progress__lte=100),
            ),
            models.CheckConstraint(
                name="characters_will_non_negative",
                condition=Q(will_power__gte=0),
            ),
            models.CheckConstraint(
                name="characters_will_progress_range",
                condition=Q(will_power_progress__gte=0) & Q(will_power_progress__lte=100),
            ),
        ]
        indexes = [
            models.Index(
                fields=["adventure", "location"],
                name="idx_characters_adv_location",
            ),
            models.Index(fields=["adventure", "is_player"], name="idx_characters_is_player"),
            models.Index(fields=["adventure", "in_party"], name="idx_characters_in_party"),
            GinIndex(fields=["tags"], name="idx_characters_tags_gin"),
        ]

    def __str__(self) -> str:
        return self.title


class ModerationEntry(models.Model):
    adventure = models.OneToOneField(
        Adventure,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name="moderation_entry",
    )
    submitted_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"Moderation: {self.adventure.title}"


class PublishedAdventure(models.Model):
    adventure = models.OneToOneField(
        Adventure,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name="publication_entry",
    )
    published_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"Published: {self.adventure.title}"


class SkillSystem(models.Model):
    adventure = models.ForeignKey(Adventure, on_delete=models.CASCADE, related_name="skill_systems")
    title = models.TextField()
    description = models.TextField(blank=True)
    tags = ArrayField(models.TextField(), default=list, blank=True)
    w_body = models.IntegerField(default=0)
    w_mind = models.IntegerField(default=0)
    w_will = models.IntegerField(default=0)
    formula_hint = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                name="skill_systems_weights_nonneg",
                condition=Q(w_body__gte=0) & Q(w_mind__gte=0) & Q(w_will__gte=0),
            ),
            models.CheckConstraint(
                name="skill_systems_weights_not_all_zero",
                condition=Q(w_body__gt=0) | Q(w_mind__gt=0) | Q(w_will__gt=0),
            ),
        ]
        indexes = [
            models.Index(fields=["adventure"], name="idx_skill_systems_adv"),
            GinIndex(fields=["tags"], name="idx_skill_systems_tags_gin"),
        ]

    def __str__(self) -> str:
        return self.title


class Technique(models.Model):
    system = models.ForeignKey(SkillSystem, on_delete=models.CASCADE, related_name="techniques")
    title = models.TextField()
    description = models.TextField(blank=True)
    tags = ArrayField(models.TextField(), default=list, blank=True)
    difficulty = models.IntegerField(default=0)
    tier = models.IntegerField(null=True, blank=True)
    required_system_level = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                name="techniques_difficulty_nonneg",
                condition=Q(difficulty__gte=0),
            ),
            models.CheckConstraint(
                name="techniques_tier_nonneg",
                condition=Q(tier__gte=0) | Q(tier__isnull=True),
            ),
            models.CheckConstraint(
                name="techniques_required_level_nonneg",
                condition=Q(required_system_level__gte=0),
            ),
        ]
        indexes = [
            GinIndex(fields=["tags"], name="idx_techniques_tags_gin"),
        ]

    def __str__(self) -> str:
        return self.title


class Faction(models.Model):
    adventure = models.ForeignKey(Adventure, on_delete=models.CASCADE, related_name="factions")
    title = models.TextField()
    description = models.TextField(blank=True)
    tags = ArrayField(models.TextField(), default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [GinIndex(fields=["tags"], name="idx_factions_tags_gin")]

    def __str__(self) -> str:
        return self.title


class OtherInfo(models.Model):
    adventure = models.ForeignKey(Adventure, on_delete=models.CASCADE, related_name="other_infos")
    category = models.TextField()
    title = models.TextField()
    description = models.TextField(blank=True)
    tags = ArrayField(models.TextField(), default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["adventure", "category"], name="idx_other_info_category"),
            GinIndex(fields=["tags"], name="idx_other_info_tags_gin"),
        ]

    def __str__(self) -> str:
        return self.title


class CharacterSystem(models.Model):
    id = models.BigAutoField(primary_key=True)
    character = models.ForeignKey(
        Character,
        on_delete=models.CASCADE,
        related_name="character_systems",
    )
    system = models.ForeignKey(
        SkillSystem,
        on_delete=models.CASCADE,
        related_name="character_systems",
    )
    level = models.IntegerField(default=0)
    progress_percent = models.IntegerField(default=0)
    notes = models.TextField(blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["character", "system"],
                name="uq_character_system",
            ),
            models.CheckConstraint(
                name="character_system_level_nonneg",
                condition=Q(level__gte=0),
            ),
            models.CheckConstraint(
                name="character_system_progress_pct",
                condition=Q(progress_percent__gte=0) & Q(progress_percent__lte=100),
            ),
        ]

    def clean(self) -> None:
        if (
            self.character_id
            and self.system_id
            and self.character.adventure_id != self.system.adventure_id
        ):
            raise ValidationError("Character/system adventure mismatch.")


class CharacterTechnique(models.Model):
    id = models.BigAutoField(primary_key=True)
    character = models.ForeignKey(
        Character,
        on_delete=models.CASCADE,
        related_name="character_techniques",
    )
    technique = models.ForeignKey(
        Technique,
        on_delete=models.CASCADE,
        related_name="character_techniques",
    )
    learned_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["character", "technique"],
                name="uq_character_technique",
            ),
        ]

    def clean(self) -> None:
        if self.character_id and self.technique_id:
            if self.character.adventure_id != self.technique.system.adventure_id:
                raise ValidationError("Character/technique adventure mismatch.")


class CharacterFaction(models.Model):
    id = models.BigAutoField(primary_key=True)
    character = models.ForeignKey(
        Character,
        on_delete=models.CASCADE,
        related_name="character_factions",
    )
    faction = models.ForeignKey(Faction, on_delete=models.CASCADE, related_name="character_factions")

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["character", "faction"],
                name="uq_characters_factions",
            ),
        ]
        indexes = [
            models.Index(fields=["character"], name="idx_char_factions_char"),
        ]

    def clean(self) -> None:
        if self.character_id and self.faction_id:
            if self.character.adventure_id != self.faction.adventure_id:
                raise ValidationError("Character/faction adventure mismatch.")


class CharacterRelationship(models.Model):
    from_character = models.ForeignKey(
        Character,
        on_delete=models.CASCADE,
        related_name="relationships_from",
    )
    to_character = models.ForeignKey(
        Character,
        on_delete=models.CASCADE,
        related_name="relationships_to",
    )
    kind = models.TextField()
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                name="rel_not_self",
                condition=~Q(from_character=F("to_character")),
            ),
            models.UniqueConstraint(
                fields=["from_character", "to_character", "kind"],
                name="uq_relationship",
            ),
        ]
        indexes = [
            models.Index(fields=["from_character"], name="idx_rel_from_char"),
            models.Index(fields=["to_character"], name="idx_rel_to_char"),
            models.Index(fields=["kind"], name="idx_rel_kind"),
        ]

    def clean(self) -> None:
        if self.from_character_id and self.to_character_id:
            if self.from_character.adventure_id != self.to_character.adventure_id:
                raise ValidationError("Relationship adventure mismatch.")


class AdventureHistory(models.Model):
    class Role(models.TextChoices):
        USER = "user", "user"
        AI = "ai", "ai"
        SYSTEM = "system", "system"

    adventure = models.ForeignKey(Adventure, on_delete=models.CASCADE, related_name="history")
    role = models.TextField(choices=Role.choices)
    content = models.TextField()
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                name="history_role_chk",
                condition=Q(role__in=["user", "ai", "system"]),
            )
        ]
        indexes = [
            models.Index(
                fields=["adventure", "-id"],
                name="idx_history_adv_entry_desc",
            ),
        ]


class AdventureMemory(models.Model):
    class Kind(models.TextChoices):
        SUMMARY = "summary", "summary"
        FACT = "fact", "fact"
        RULE = "rule", "rule"
        GOAL = "goal", "goal"

    adventure = models.ForeignKey(Adventure, on_delete=models.CASCADE, related_name="memories")
    kind = models.TextField(choices=Kind.choices)
    title = models.TextField(blank=True)
    content = models.TextField()
    importance = models.IntegerField(default=0)
    tags = ArrayField(models.TextField(), default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                name="memories_kind_chk",
                condition=Q(kind__in=["summary", "fact", "rule", "goal"]),
            )
        ]
        indexes = [
            models.Index(
                fields=["adventure", "-importance"],
                name="idx_memories_adv_importance",
            ),
            GinIndex(fields=["tags"], name="idx_memories_tags_gin"),
        ]


class AdventureEvent(models.Model):
    class Status(models.TextChoices):
        INACTIVE = "inactive", "inactive"
        ACTIVE = "active", "active"
        RESOLVED = "resolved", "resolved"

    adventure = models.ForeignKey(Adventure, on_delete=models.CASCADE, related_name="events")
    location = models.ForeignKey(
        Location,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="events",
    )
    status = models.TextField(choices=Status.choices, default=Status.INACTIVE)
    title = models.TextField()
    trigger_hint = models.TextField(blank=True)
    state = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                name="events_status_chk",
                condition=Q(status__in=["inactive", "active", "resolved"]),
            )
        ]
        indexes = [
            models.Index(fields=["adventure", "status"], name="idx_events_adv_status"),
            models.Index(fields=["adventure", "location", "status"], name="idx_events_adv_loc_status"),
        ]

    def __str__(self) -> str:
        return self.title


class LearningObjective(models.Model):
    class Competency(models.TextChoices):
        EMPATHY = "empathy", "empathy"
        COOPERATION = "cooperation", "cooperation"
        SELF_REGULATION = "self_regulation", "self_regulation"
        RESPONSIBLE_DECISION = "responsible_decision", "responsible_decision"
        RESTORATIVE_ACTION = "restorative_action", "restorative_action"
        HELP_SEEKING = "help_seeking", "help_seeking"
        INCLUSION = "inclusion", "inclusion"

    adventure = models.ForeignKey(
        Adventure,
        on_delete=models.CASCADE,
        related_name="learning_objectives",
    )
    code = models.SlugField(max_length=64)
    title = models.TextField()
    description = models.TextField(blank=True)
    competency = models.TextField(choices=Competency.choices)
    weight = models.PositiveSmallIntegerField(default=1)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["adventure", "code"],
                name="uq_learning_objective_code",
            ),
            models.CheckConstraint(
                name="learning_objective_competency_chk",
                condition=Q(
                    competency__in=[
                        "empathy",
                        "cooperation",
                        "self_regulation",
                        "responsible_decision",
                        "restorative_action",
                        "help_seeking",
                        "inclusion",
                    ]
                ),
            ),
            models.CheckConstraint(
                name="learning_objective_weight_range",
                condition=Q(weight__gte=1) & Q(weight__lte=5),
            ),
        ]
        indexes = [
            models.Index(fields=["adventure", "is_active"], name="idx_learning_obj_active"),
            models.Index(fields=["competency"], name="idx_learning_obj_competency"),
        ]

    def __str__(self) -> str:
        return f"{self.code}: {self.title}"


class AccessibilityProfile(models.Model):
    class Locale(models.TextChoices):
        RU = "ru", "ru"
        EN = "en", "en"
        ZH_CN = "zh-CN", "zh-CN"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="accessibility_profile",
    )
    locale = models.CharField(max_length=8, choices=Locale.choices, default=Locale.RU)
    simple_language = models.BooleanField(default=False)
    high_contrast = models.BooleanField(default=False)
    reduced_text_length = models.BooleanField(default=False)
    choice_cards_enabled = models.BooleanField(default=True)
    content_warnings_enabled = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)


class LearnerProfile(models.Model):
    class AgeBand(models.TextChoices):
        AGE_15_18 = "15-18", "15-18"
        AGE_18_PLUS = "18+", "18+"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="learner_profile",
    )
    age_band = models.CharField(max_length=16, choices=AgeBand.choices, default=AgeBand.AGE_15_18)
    consent_confirmed = models.BooleanField(default=False)
    notes = models.TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)


class ReflectionPrompt(models.Model):
    class TriggerKind(models.TextChoices):
        USER_TURN = "user_turn", "user_turn"
        AI_TURN = "ai_turn", "ai_turn"
        KEY_CHOICE = "key_choice", "key_choice"

    adventure = models.ForeignKey(Adventure, on_delete=models.CASCADE, related_name="reflection_prompts")
    objective = models.ForeignKey(
        LearningObjective,
        on_delete=models.CASCADE,
        related_name="reflection_prompts",
    )
    trigger_kind = models.CharField(
        max_length=32,
        choices=TriggerKind.choices,
        default=TriggerKind.KEY_CHOICE,
    )
    question = models.TextField()
    is_active = models.BooleanField(default=True)

    class Meta:
        indexes = [
            models.Index(fields=["adventure", "is_active"], name="idx_reflection_active"),
        ]


class ReflectionResponse(models.Model):
    adventure = models.ForeignKey(Adventure, on_delete=models.CASCADE, related_name="reflection_responses")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reflection_responses",
    )
    prompt = models.ForeignKey(
        ReflectionPrompt,
        on_delete=models.CASCADE,
        related_name="responses",
    )
    history_entry = models.ForeignKey(
        AdventureHistory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reflection_responses",
    )
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["adventure", "user", "-created_at"], name="idx_reflection_user"),
        ]


class BehaviorEvidence(models.Model):
    adventure = models.ForeignKey(Adventure, on_delete=models.CASCADE, related_name="behavior_evidence")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="behavior_evidence",
    )
    history_entry = models.ForeignKey(
        AdventureHistory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="behavior_evidence",
    )
    reflection_response = models.ForeignKey(
        ReflectionResponse,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="behavior_evidence",
    )
    competency = models.TextField(choices=LearningObjective.Competency.choices)
    marker = models.CharField(max_length=128)
    score = models.SmallIntegerField(default=0)
    confidence = models.FloatField(default=0.5)
    excerpt = models.TextField(blank=True)
    rationale = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                name="behavior_evidence_score_range",
                condition=Q(score__gte=-2) & Q(score__lte=2),
            ),
            models.CheckConstraint(
                name="behavior_evidence_confidence_range",
                condition=Q(confidence__gte=0.0) & Q(confidence__lte=1.0),
            ),
        ]
        indexes = [
            models.Index(fields=["adventure", "user", "-created_at"], name="idx_evidence_user"),
            models.Index(fields=["competency"], name="idx_evidence_competency"),
        ]


class RepairOpportunity(models.Model):
    class Status(models.TextChoices):
        OPEN = "open", "open"
        IN_PROGRESS = "in_progress", "in_progress"
        RESOLVED = "resolved", "resolved"
        DISMISSED = "dismissed", "dismissed"

    adventure = models.ForeignKey(
        Adventure,
        on_delete=models.CASCADE,
        related_name="repair_opportunities",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="repair_opportunities",
        null=True,
        blank=True,
    )
    source_history_entry = models.ForeignKey(
        AdventureHistory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="repair_opportunities",
    )
    source_evidence = models.OneToOneField(
        BehaviorEvidence,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="repair_opportunity",
    )
    related_event = models.ForeignKey(
        AdventureEvent,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="repair_opportunities",
    )
    competency = models.TextField(choices=LearningObjective.Competency.choices)
    status = models.CharField(max_length=32, choices=Status.choices, default=Status.OPEN)
    title = models.TextField()
    description = models.TextField(blank=True)
    suggested_action = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["adventure", "status"], name="idx_repair_adv_status"),
            models.Index(fields=["adventure", "competency"], name="idx_repair_adv_comp"),
            models.Index(fields=["user", "status"], name="idx_repair_user_status"),
        ]


class ConsequenceMarker(models.Model):
    class Kind(models.TextChoices):
        CONSTRUCTIVE_CHOICE = "constructive_choice", "constructive_choice"
        GROWTH_OPPORTUNITY = "growth_opportunity", "growth_opportunity"
        REPAIR_OPENED = "repair_opened", "repair_opened"
        SAFETY_WARNING = "safety_warning", "safety_warning"

    adventure = models.ForeignKey(
        Adventure,
        on_delete=models.CASCADE,
        related_name="consequence_markers",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="consequence_markers",
        null=True,
        blank=True,
    )
    history_entry = models.ForeignKey(
        AdventureHistory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="consequence_markers",
    )
    evidence = models.OneToOneField(
        BehaviorEvidence,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="consequence_marker",
    )
    competency = models.TextField(
        choices=LearningObjective.Competency.choices,
        null=True,
        blank=True,
    )
    kind = models.CharField(max_length=32, choices=Kind.choices)
    title = models.TextField()
    description = models.TextField(blank=True)
    weight = models.SmallIntegerField(default=0)
    tags = ArrayField(models.TextField(), default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["adventure", "-created_at"], name="idx_conseq_adv_created"),
            models.Index(fields=["adventure", "kind"], name="idx_conseq_adv_kind"),
            models.Index(fields=["user", "-created_at"], name="idx_conseq_user_created"),
            GinIndex(fields=["tags"], name="idx_conseq_tags_gin"),
        ]


class NarrativeConsequence(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "active"
        RESOLVED = "resolved", "resolved"
        ARCHIVED = "archived", "archived"

    class Certainty(models.TextChoices):
        INTENT = "intent", "intent"
        ATTEMPTED = "attempted", "attempted"
        ESTABLISHED = "established", "established"

    adventure = models.ForeignKey(
        Adventure,
        on_delete=models.CASCADE,
        related_name="narrative_consequences",
    )
    source_history_entry = models.ForeignKey(
        AdventureHistory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="narrative_consequences",
    )
    title = models.TextField()
    summary = models.TextField()
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.ACTIVE)
    certainty = models.CharField(
        max_length=16,
        choices=Certainty.choices,
        default=Certainty.ESTABLISHED,
    )
    importance = models.PositiveSmallIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                name="narrative_consequence_importance_range",
                condition=Q(importance__gte=1) & Q(importance__lte=5),
            ),
        ]
        indexes = [
            models.Index(
                fields=["adventure", "status", "certainty", "-importance", "-updated_at"],
                name="idx_narrative_conseq_scope",
            ),
        ]


class NarrativeConsequenceCharacter(models.Model):
    consequence = models.ForeignKey(
        NarrativeConsequence,
        on_delete=models.CASCADE,
        related_name="character_links",
    )
    character = models.ForeignKey(
        Character,
        on_delete=models.CASCADE,
        related_name="narrative_consequence_links",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["consequence", "character"],
                name="uq_narrative_conseq_character",
            ),
        ]
        indexes = [
            models.Index(fields=["character"], name="idx_narrative_conseq_char"),
        ]

    def clean(self) -> None:
        if self.consequence_id and self.character_id:
            if self.consequence.adventure_id != self.character.adventure_id:
                raise ValidationError("Narrative consequence/character adventure mismatch.")


class NarrativeConsequenceLocation(models.Model):
    consequence = models.ForeignKey(
        NarrativeConsequence,
        on_delete=models.CASCADE,
        related_name="location_links",
    )
    location = models.ForeignKey(
        Location,
        on_delete=models.CASCADE,
        related_name="narrative_consequence_links",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["consequence", "location"],
                name="uq_narrative_conseq_location",
            ),
        ]
        indexes = [
            models.Index(fields=["location"], name="idx_narrative_conseq_loc"),
        ]

    def clean(self) -> None:
        if self.consequence_id and self.location_id:
            if self.consequence.adventure_id != self.location.adventure_id:
                raise ValidationError("Narrative consequence/location adventure mismatch.")


class NarrativeConsequenceFaction(models.Model):
    consequence = models.ForeignKey(
        NarrativeConsequence,
        on_delete=models.CASCADE,
        related_name="faction_links",
    )
    faction = models.ForeignKey(
        Faction,
        on_delete=models.CASCADE,
        related_name="narrative_consequence_links",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["consequence", "faction"],
                name="uq_narrative_conseq_faction",
            ),
        ]
        indexes = [
            models.Index(fields=["faction"], name="idx_narrative_conseq_faction"),
        ]

    def clean(self) -> None:
        if self.consequence_id and self.faction_id:
            if self.consequence.adventure_id != self.faction.adventure_id:
                raise ValidationError("Narrative consequence/faction adventure mismatch.")


class TurnAnalysisLog(models.Model):
    class Kind(models.TextChoices):
        PLAYER_TURN = "player_turn", "player_turn"
        WORLD_CONFIRMATION = "world_confirmation", "world_confirmation"

    class Status(models.TextChoices):
        OK = "ok", "ok"
        INVALID_OUTPUT = "invalid_output", "invalid_output"
        ERROR = "error", "error"

    adventure = models.ForeignKey(
        Adventure,
        on_delete=models.CASCADE,
        related_name="turn_analysis_logs",
    )
    history_entry = models.ForeignKey(
        AdventureHistory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="turn_analysis_logs",
    )
    kind = models.CharField(max_length=32, choices=Kind.choices)
    status = models.CharField(max_length=32, choices=Status.choices)
    raw_response = models.TextField(blank=True)
    error = models.TextField(blank=True)
    result_counts = models.JSONField(default=dict, blank=True)
    snapshot = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["adventure", "-created_at"], name="idx_turn_analysis_adv"),
            models.Index(fields=["status", "-created_at"], name="idx_turn_analysis_status"),
        ]


class PedagogicalIntervention(models.Model):
    class Kind(models.TextChoices):
        DILEMMA = "dilemma", "dilemma"
        REPAIR = "repair", "repair"
        PERSPECTIVE = "perspective", "perspective"
        CHOICE_CARDS = "choice_cards", "choice_cards"

    adventure = models.ForeignKey(Adventure, on_delete=models.CASCADE, related_name="pedagogical_interventions")
    objective = models.ForeignKey(
        LearningObjective,
        on_delete=models.CASCADE,
        related_name="interventions",
    )
    kind = models.CharField(max_length=32, choices=Kind.choices)
    payload = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        indexes = [
            models.Index(fields=["adventure", "kind", "is_active"], name="idx_intervention_kind"),
        ]


class SafetyReview(models.Model):
    class RiskLevel(models.TextChoices):
        LOW = "low", "low"
        MEDIUM = "medium", "medium"
        HIGH = "high", "high"

    class Action(models.TextChoices):
        ALLOW = "allow", "allow"
        WARN = "warn", "warn"
        BLOCK = "block", "block"

    adventure = models.ForeignKey(Adventure, on_delete=models.CASCADE, related_name="safety_reviews")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="safety_reviews",
        null=True,
        blank=True,
    )
    history_entry = models.ForeignKey(
        AdventureHistory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="safety_reviews",
    )
    source = models.CharField(max_length=32)
    risk_level = models.CharField(max_length=16, choices=RiskLevel.choices, default=RiskLevel.LOW)
    categories = models.JSONField(default=list, blank=True)
    action = models.CharField(max_length=16, choices=Action.choices, default=Action.ALLOW)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["adventure", "-created_at"], name="idx_safety_adventure"),
            models.Index(fields=["risk_level", "action"], name="idx_safety_risk_action"),
        ]
