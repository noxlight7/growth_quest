import json
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from rest_framework.test import APIClient

from backend.llm import LLMResponse

from adventures.models import (
    Adventure,
    AdventureEvent,
    AdventureHeroSetup,
    AdventureHistory,
    AdventureMemory,
    AdventurePlayer,
    BehaviorEvidence,
    Character,
    CharacterFaction,
    CharacterRelationship,
    CharacterSystem,
    CharacterTechnique,
    ConsequenceMarker,
    Faction,
    LearningObjective,
    Location,
    NarrativeConsequence,
    OtherInfo,
    PedagogicalIntervention,
    PublishedAdventure,
    Race,
    RepairOpportunity,
    ReflectionPrompt,
    ReflectionResponse,
    SafetyReview,
    SkillSystem,
    Technique,
    TurnAnalysisLog,
)
from adventures.schemas.llm import EvidenceItem, parse_evaluator_output, parse_turn_analysis_output
from adventures.services.evaluation import (
    extract_llm_evidence,
    extract_observable_evidence,
    save_evidence,
)
from adventures.services.narrative_consequences import (
    apply_narrative_consequence_updates,
    build_narrative_consequence_context,
    get_relevant_narrative_consequences,
)
from adventures.services.orchestrator import after_ai_turn, after_user_turn, before_user_turn
from adventures.services.pedagogy import choose_objective, choose_reflection_prompt, get_choice_cards
from adventures.services.safety import review_text
from adventures.services.turn_analysis import (
    _build_turn_analysis_prompt,
    analyze_and_persist_turn,
    analyze_and_persist_world_confirmation,
    analyze_turn,
    persist_turn_analysis,
    revert_analysis_for_history_entries,
)
from adventures.views.history_utils import (
    _apply_card_updates,
    _extract_json_payload,
    _prepare_history_for_prompt,
)
from adventures.views.ai_views import format_player_move_content
from adventures.views.prompts import (
    _build_card_update_prompt,
    _build_generation_prompt,
    _build_npc_generation_prompt,
    _split_party_characters,
)


class FakeEvidenceClient:
    def __init__(self, text: str):
        self.text = text

    def generate(self, *args, **kwargs):
        return LLMResponse(text=self.text, raw={"provider": "fake"})


class FakeHistoryUpdateClient:
    def __init__(self):
        self.prompts = []

    def generate(self, prompt: str, *args, **kwargs):
        self.prompts.append(prompt)
        return LLMResponse(
            text='{"events":[],"characters":[],"character_systems":[],'
            '"character_techniques":[],"memories":[],"relationships":[],'
            '"repair_opportunities":[],"consequence_markers":[]}',
            raw={"provider": "fake"},
        )


class FakeTemplateTranslationClient:
    def __init__(self):
        self.prompts = []

    def generate(self, prompt: str, *args, **kwargs):
        self.prompts.append(prompt)
        items = json.loads(prompt.split("Input: ", 1)[1])
        return LLMResponse(
            text=json.dumps(
                {
                    "translations": [
                        {"key": item["key"], "text": f"translated::{item['text']}"}
                        for item in items
                    ]
                }
            ),
            raw={"provider": "fake"},
        )


class LearningServiceTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username="learner", password="pass")
        self.adventure = Adventure.objects.create(
            author_user=self.user,
            player_user=None,
            template_adventure=None,
            is_template=True,
            title="Template",
            growth_analysis_enabled=True,
            narrative_consequences_enabled=True,
        )

    def test_invalid_evaluator_json_falls_back_to_empty_list(self):
        self.assertEqual(parse_evaluator_output("not-json"), [])

    def test_invalid_turn_analysis_json_falls_back_to_empty_sections(self):
        analysis = parse_turn_analysis_output("not-json")

        self.assertEqual(analysis.evidence, [])
        self.assertEqual(analysis.repair_opportunities, [])
        self.assertEqual(analysis.narrative_consequences, [])

    def test_card_update_json_extractor_recovers_embedded_object(self):
        self.assertEqual(
            _extract_json_payload('Model note: {"events": []}'),
            {"events": []},
        )

    def test_llm_evaluator_keeps_only_supported_observable_evidence(self):
        text = "I pause, listen to Mira, and ask the teacher for help."
        client = FakeEvidenceClient(
            """
            {
              "evidence": [
                {
                  "competency": "empathy",
                  "marker": "listened_to_npc",
                  "score": 1,
                  "confidence": 0.82,
                  "excerpt": "listen to Mira",
                  "rationale": "The player chose to listen."
                },
                {
                  "competency": "inclusion",
                  "marker": "unsupported_claim",
                  "score": 1,
                  "confidence": 0.92,
                  "excerpt": "invites everyone",
                  "rationale": "This is not in the text."
                },
                {
                  "competency": "personality",
                  "marker": "hidden_profile",
                  "score": 1,
                  "confidence": 0.99,
                  "excerpt": "I pause",
                  "rationale": "Invalid competency."
                }
              ]
            }
            """
        )

        evidence = extract_llm_evidence(text, client=client)

        self.assertEqual(len(evidence), 1)
        self.assertEqual(evidence[0].competency, "empathy")
        self.assertEqual(evidence[0].excerpt, "listen to Mira")

    def test_observable_evaluator_uses_supported_llm_evidence_without_keyword_rules(self):
        text = "I pause, listen to Mira, and ask the teacher for help."
        client = FakeEvidenceClient(
            """
            {
              "evidence": [
                {
                  "competency": "empathy",
                  "marker": "listened_to_npc",
                  "score": 1,
                  "confidence": 0.82,
                  "excerpt": "listen to Mira",
                  "rationale": "The player chose to listen."
                }
              ]
            }
            """
        )

        evidence = extract_observable_evidence(text, client=client)

        self.assertEqual([item.competency for item in evidence], ["empathy"])

    def test_model_failure_does_not_synthesize_evidence_or_moral_markers(self):
        entry = AdventureHistory.objects.create(
            adventure=self.adventure,
            role=AdventureHistory.Role.USER,
            content="I pause, ask the teacher for help, and include the new classmate.",
        )
        items = extract_observable_evidence(entry.content, client=FakeEvidenceClient("not-json"))
        created = save_evidence(self.adventure, self.user, items, history_entry=entry)

        self.assertEqual(created, [])
        self.assertFalse(BehaviorEvidence.objects.filter(adventure=self.adventure).exists())
        self.assertFalse(ConsequenceMarker.objects.filter(adventure=self.adventure).exists())

    def test_turn_analysis_creates_explicit_repair_state(self):
        LearningObjective.objects.create(
            adventure=self.adventure,
            code="empathy",
            title="Empathy",
            competency="empathy",
        )
        entry = AdventureHistory.objects.create(
            adventure=self.adventure,
            role=AdventureHistory.Role.USER,
            content="I ignore the new classmate and exclude them from the team.",
        )
        client = FakeEvidenceClient(
            """
            {
              "evidence": [{
                "competency": "empathy",
                "marker": "excluded_teammate",
                "score": -1,
                "confidence": 0.88,
                "excerpt": "exclude them from the team",
                "rationale": "The player visibly excludes a teammate."
              }],
              "repair_opportunities": [{
                "competency": "empathy",
                "title": "The classmate keeps their distance",
                "description": "A later scene can leave room to rebuild trust.",
                "suggested_action": "Let the party offer a credible role in the plan."
              }],
              "narrative_consequences": []
            }
            """
        )

        analysis = analyze_turn(self.adventure, entry, client=client)
        persist_turn_analysis(self.adventure, self.user, entry, analysis)

        repair = RepairOpportunity.objects.get(adventure=self.adventure, competency="empathy")
        self.assertEqual(repair.competency, "empathy")
        self.assertEqual(repair.status, RepairOpportunity.Status.OPEN)
        self.assertEqual(repair.source_history_entry, entry)
        self.assertEqual(repair.source_evidence.marker, "excluded_teammate")
        self.assertFalse(ConsequenceMarker.objects.filter(adventure=self.adventure).exists())

    def test_turn_analysis_ignores_repair_outside_active_objectives(self):
        LearningObjective.objects.create(
            adventure=self.adventure,
            code="empathy",
            title="Empathy",
            competency="empathy",
        )
        entry = AdventureHistory.objects.create(
            adventure=self.adventure,
            role=AdventureHistory.Role.USER,
            content="I leave the room.",
        )
        client = FakeEvidenceClient(
            """
            {
              "evidence": [],
              "repair_opportunities": [{
                "competency": "inclusion",
                "title": "Unexpected repair"
              }],
              "narrative_consequences": []
            }
            """
        )

        analysis = analyze_turn(self.adventure, entry, client=client)
        persist_turn_analysis(self.adventure, self.user, entry, analysis)

        self.assertEqual(analysis.repair_opportunities, [])
        self.assertFalse(RepairOpportunity.objects.filter(adventure=self.adventure).exists())

    def test_turn_analysis_stores_moral_narrative_consequence_with_entity_links(self):
        harbor = Location.objects.create(adventure=self.adventure, title="Harbor")
        guild = Faction.objects.create(adventure=self.adventure, title="Lantern Guild")
        mira = Character.objects.create(
            adventure=self.adventure,
            title="Mira",
            location=harbor,
            in_party=True,
        )
        CharacterFaction.objects.create(character=mira, faction=guild)
        entry = AdventureHistory.objects.create(
            adventure=self.adventure,
            role=AdventureHistory.Role.USER,
            content="I stay behind to help Mira repair the lanterns before the storm.",
        )
        client = FakeEvidenceClient(
            f"""
            {{
              "evidence": [],
              "repair_opportunities": [],
              "narrative_consequences": [{{
                "title": "Lanterns repaired before the storm",
                "summary": "The hero stayed behind to help Mira repair the harbor lanterns.",
                "importance": 4,
                "characters": [{mira.id}],
                "locations": [{harbor.id}],
                "factions": [{guild.id}]
              }}]
            }}
            """
        )

        analysis = analyze_turn(self.adventure, entry, client=client)
        persist_turn_analysis(self.adventure, self.user, entry, analysis)

        consequence = NarrativeConsequence.objects.get(adventure=self.adventure)
        self.assertEqual(consequence.title, "Lanterns repaired before the storm")
        self.assertEqual(consequence.certainty, NarrativeConsequence.Certainty.ATTEMPTED)
        self.assertEqual(consequence.character_links.get().character, mira)
        self.assertEqual(consequence.location_links.get().location, harbor)
        self.assertEqual(consequence.faction_links.get().faction, guild)
        self.assertFalse(
            any(
                field.name in {"valence", "moral_score", "karma"}
                for field in NarrativeConsequence._meta.fields
            )
        )

    def test_player_declared_outcome_enters_story_memory_only_after_world_confirmation(self):
        entry = AdventureHistory.objects.create(
            adventure=self.adventure,
            role=AdventureHistory.Role.USER,
            content="I demand that the dark deity grant me invincible power.",
        )
        player_client = FakeEvidenceClient(
            """
            {
              "evidence": [],
              "repair_opportunities": [],
              "narrative_consequences": [{
                "certainty": "established",
                "title": "Requested dark blessing",
                "summary": "The hero demanded an invincible blessing from the dark deity.",
                "importance": 4
              }]
            }
            """
        )

        analysis = analyze_turn(self.adventure, entry, client=player_client)
        persist_turn_analysis(self.adventure, self.user, entry, analysis)

        consequence = NarrativeConsequence.objects.get(adventure=self.adventure)
        self.assertEqual(consequence.certainty, NarrativeConsequence.Certainty.ATTEMPTED)
        self.assertNotIn("Requested dark blessing", _build_generation_prompt(self.adventure, [entry]))

        world_entry = AdventureHistory.objects.create(
            adventure=self.adventure,
            role=AdventureHistory.Role.AI,
            content="The deity answers with a visible dark aura, but the blessing leaves a painful mark.",
        )
        world_client = FakeEvidenceClient(
            f"""
            {{
              "narrative_consequences": [{{
                "id": {consequence.id},
                "certainty": "established",
                "title": "Costly dark blessing",
                "summary": "The deity granted a visible dark aura that left a painful mark.",
                "importance": 4
              }}]
            }}
            """
        )

        analyze_and_persist_world_confirmation(
            self.adventure,
            world_entry,
            client=world_client,
        )

        consequence.refresh_from_db()
        self.assertEqual(consequence.certainty, NarrativeConsequence.Certainty.ESTABLISHED)
        self.assertEqual(consequence.title, "Costly dark blessing")
        self.assertIn(
            "Costly dark blessing",
            _build_generation_prompt(self.adventure, [entry, world_entry]),
        )

        revert_analysis_for_history_entries(self.adventure, [world_entry])

        consequence.refresh_from_db()
        self.assertEqual(consequence.certainty, NarrativeConsequence.Certainty.ATTEMPTED)
        self.assertEqual(consequence.title, "Requested dark blessing")

    def test_player_turn_does_not_rewrite_established_consequence(self):
        established = apply_narrative_consequence_updates(
            self.adventure,
            [
                {
                    "title": "Mira received a lantern",
                    "summary": "Mira received a lantern during an earlier scene.",
                    "importance": 3,
                }
            ],
        )[0]
        entry = AdventureHistory.objects.create(
            adventure=self.adventure,
            role=AdventureHistory.Role.USER,
            content="I insist that Mira hand the lantern back to me.",
        )
        client = FakeEvidenceClient(
            f"""
            {{
              "evidence": [],
              "repair_opportunities": [],
              "narrative_consequences": [{{
                "id": {established.id},
                "certainty": "established",
                "title": "Mira returned the lantern",
                "summary": "Mira returned the lantern to the hero.",
                "importance": 3
              }}]
            }}
            """
        )

        analysis = analyze_turn(self.adventure, entry, client=client)
        persist_turn_analysis(self.adventure, self.user, entry, analysis)

        established.refresh_from_db()
        attempted = NarrativeConsequence.objects.exclude(id=established.id).get(
            adventure=self.adventure
        )
        self.assertEqual(established.title, "Mira received a lantern")
        self.assertEqual(
            established.summary,
            "Mira received a lantern during an earlier scene.",
        )
        self.assertEqual(established.certainty, NarrativeConsequence.Certainty.ESTABLISHED)
        self.assertEqual(attempted.title, "Mira returned the lantern")
        self.assertEqual(attempted.certainty, NarrativeConsequence.Certainty.ATTEMPTED)

    def test_invalid_turn_analysis_output_is_logged(self):
        entry = AdventureHistory.objects.create(
            adventure=self.adventure,
            role=AdventureHistory.Role.USER,
            content="I walk toward the gate.",
        )

        analyze_and_persist_turn(
            self.adventure,
            self.user,
            entry,
            client=FakeEvidenceClient("not-json"),
        )

        log = TurnAnalysisLog.objects.get(adventure=self.adventure, history_entry=entry)
        self.assertEqual(log.kind, TurnAnalysisLog.Kind.PLAYER_TURN)
        self.assertEqual(log.status, TurnAnalysisLog.Status.INVALID_OUTPUT)

    def test_world_confirmation_removes_dead_npc_from_party_and_updates_event(self):
        event = AdventureEvent.objects.create(
            adventure=self.adventure,
            title="Harbor attack",
            status=AdventureEvent.Status.ACTIVE,
            state="The harbor is under attack.",
        )
        mira = Character.objects.create(
            adventure=self.adventure,
            title="Mira",
            in_party=True,
        )
        world_entry = AdventureHistory.objects.create(
            adventure=self.adventure,
            role=AdventureHistory.Role.AI,
            content="Mira dies defending the gate. The surviving attackers retreat from the harbor.",
        )
        client = FakeEvidenceClient(
            f"""
            {{
              "events": [{{
                "id": {event.id},
                "status": "resolved",
                "state": "The attackers retreated after Mira died defending the gate."
              }}],
              "characters": [{{
                "id": {mira.id},
                "story_status": "dead"
              }}],
              "narrative_consequences": []
            }}
            """
        )

        analyze_and_persist_world_confirmation(self.adventure, world_entry, client=client)

        event.refresh_from_db()
        mira.refresh_from_db()
        _, npc_characters = _split_party_characters(self.adventure)
        self.assertEqual(event.status, AdventureEvent.Status.RESOLVED)
        self.assertEqual(mira.story_status, Character.StoryStatus.DEAD)
        self.assertFalse(mira.in_party)
        self.assertNotIn(mira, npc_characters)

        revert_analysis_for_history_entries(self.adventure, [world_entry])

        event.refresh_from_db()
        mira.refresh_from_db()
        self.assertEqual(event.status, AdventureEvent.Status.ACTIVE)
        self.assertEqual(mira.story_status, Character.StoryStatus.ACTIVE)
        self.assertTrue(mira.in_party)

    def test_narrative_consequence_context_is_bounded_and_prefers_linked_entities(self):
        harbor = Location.objects.create(adventure=self.adventure, title="Harbor")
        market = Location.objects.create(adventure=self.adventure, title="Market")
        mira = Character.objects.create(
            adventure=self.adventure,
            title="Mira",
            location=harbor,
            in_party=True,
        )
        linked = apply_narrative_consequence_updates(
            self.adventure,
            [
                {
                    "title": "Mira remembers the lantern repair",
                    "summary": "Mira saw the hero repair the lanterns before leaving.",
                    "importance": 1,
                    "characters": [mira.id],
                    "locations": [harbor.id],
                }
            ],
        )[0]
        for index in range(45):
            apply_narrative_consequence_updates(
                self.adventure,
                [
                    {
                        "title": f"Market memory {index}",
                        "summary": f"An unrelated market event number {index}.",
                        "importance": 5,
                        "locations": [market.id],
                    }
                ],
            )

        relevant = get_relevant_narrative_consequences(
            self.adventure,
            current_location_id=harbor.id,
            character_ids={mira.id},
        )
        context = build_narrative_consequence_context(
            self.adventure,
            current_location_id=harbor.id,
            character_ids={mira.id},
        )

        self.assertLessEqual(len(relevant), 12)
        self.assertEqual(relevant[0]["id"], linked.id)
        self.assertIn("Mira remembers the lantern repair", context)
        self.assertIn('"title": "Mira"', context)

    def test_narrative_consequence_links_reject_entities_from_other_adventures(self):
        harbor = Location.objects.create(adventure=self.adventure, title="Harbor")
        other_adventure = Adventure.objects.create(
            author_user=self.user,
            player_user=None,
            template_adventure=None,
            is_template=True,
            title="Other template",
        )
        foreign_location = Location.objects.create(adventure=other_adventure, title="Foreign harbor")

        consequence = apply_narrative_consequence_updates(
            self.adventure,
            [
                {
                    "title": "Harbor watch changed",
                    "summary": "The harbor watch changed after the latest scene.",
                    "locations": [harbor.id, foreign_location.id],
                }
            ],
        )[0]

        self.assertEqual(
            list(consequence.location_links.values_list("location_id", flat=True)),
            [harbor.id],
        )

    def test_card_update_applies_growth_world_state(self):
        LearningObjective.objects.create(
            adventure=self.adventure,
            code="inclusion",
            title="Inclusion",
            competency="inclusion",
        )
        hero = Character.objects.create(
            adventure=self.adventure,
            title="Hero",
            is_player=True,
            in_party=True,
        )
        classmate = Character.objects.create(
            adventure=self.adventure,
            title="Classmate",
            in_party=True,
        )
        entry = AdventureHistory.objects.create(
            adventure=self.adventure,
            role=AdventureHistory.Role.AI,
            content="The group notices trust can be repaired.",
        )

        _apply_card_updates(
            self.adventure,
            {
                "memories": [
                    {
                        "kind": "fact",
                        "title": "Trust changed",
                        "content": "The team saw that exclusion damaged trust.",
                        "importance": 3,
                        "tags": ["trust", "repair"],
                    }
                ],
                "relationships": [
                    {
                        "from_character": hero.id,
                        "to_character": classmate.id,
                        "kind": "trust",
                        "description": "Trust is fragile but recoverable.",
                    }
                ],
                "repair_opportunities": [
                    {
                        "competency": "inclusion",
                        "status": "open",
                        "title": "Invite the classmate back",
                        "description": "The group can repair exclusion.",
                        "suggested_action": "Ask what support would help participation.",
                    }
                ],
                "consequence_markers": [
                    {
                        "kind": "growth_opportunity",
                        "competency": "inclusion",
                        "title": "Trust decreased",
                        "description": "A teammate was left out.",
                        "weight": -1,
                        "tags": ["trust"],
                    }
                ],
                "narrative_consequences": [
                    {
                        "title": "Classmate remembers the exclusion",
                        "summary": "The classmate saw the group leave without them.",
                        "importance": 3,
                        "characters": [classmate.id],
                    }
                ],
            },
            source_history_entry=entry,
        )

        self.assertTrue(AdventureMemory.objects.filter(adventure=self.adventure).exists())
        self.assertTrue(
            CharacterRelationship.objects.filter(
                from_character=hero,
                to_character=classmate,
                kind="trust",
            ).exists()
        )
        repair = RepairOpportunity.objects.get(adventure=self.adventure, competency="inclusion")
        self.assertEqual(repair.source_history_entry, entry)
        self.assertTrue(
            ConsequenceMarker.objects.filter(
                adventure=self.adventure,
                history_entry=entry,
                kind=ConsequenceMarker.Kind.GROWTH_OPPORTUNITY,
            ).exists()
        )
        narrative_consequence = NarrativeConsequence.objects.get(
            adventure=self.adventure,
            title="Classmate remembers the exclusion",
        )
        self.assertEqual(narrative_consequence.character_links.get().character, classmate)

    def test_card_update_ignores_growth_state_without_active_objectives(self):
        entry = AdventureHistory.objects.create(
            adventure=self.adventure,
            role=AdventureHistory.Role.AI,
            content="The group enters the harbor.",
        )

        _apply_card_updates(
            self.adventure,
            {
                "repair_opportunities": [
                    {
                        "competency": "empathy",
                        "title": "Unexpected repair",
                    }
                ],
                "consequence_markers": [
                    {
                        "kind": "growth_opportunity",
                        "competency": "empathy",
                        "title": "Unexpected marker",
                    }
                ],
            },
            source_history_entry=entry,
        )

        self.assertFalse(RepairOpportunity.objects.filter(adventure=self.adventure).exists())
        self.assertFalse(ConsequenceMarker.objects.filter(adventure=self.adventure).exists())

        LearningObjective.objects.create(
            adventure=self.adventure,
            code="empathy",
            title="Empathy",
            competency="empathy",
        )
        self.adventure.growth_analysis_enabled = False
        self.adventure.save(update_fields=["growth_analysis_enabled"])

        _apply_card_updates(
            self.adventure,
            {
                "repair_opportunities": [
                    {
                        "competency": "empathy",
                        "title": "Disabled repair",
                    }
                ],
                "consequence_markers": [
                    {
                        "kind": "growth_opportunity",
                        "competency": "empathy",
                        "title": "Disabled marker",
                    }
                ],
            },
            source_history_entry=entry,
        )

        self.assertFalse(RepairOpportunity.objects.filter(adventure=self.adventure).exists())
        self.assertFalse(ConsequenceMarker.objects.filter(adventure=self.adventure).exists())

    def test_history_compaction_analyzes_oldest_uncompacted_posts(self):
        entries = [
            AdventureHistory.objects.create(
                adventure=self.adventure,
                role=AdventureHistory.Role.USER,
                content=f"old-post-{index}",
            )
            for index in range(1, 7)
        ]
        client = FakeHistoryUpdateClient()

        with patch.dict(
            "os.environ",
            {
                "HISTORY_MAX_PROMPT_POSTS": "5",
                "HISTORY_TAIL_UPDATE_POSTS": "2",
            },
        ):
            prepared = _prepare_history_for_prompt(self.adventure, client)

        self.assertEqual([entry.id for entry in prepared], [entry.id for entry in entries[2:]])
        self.adventure.refresh_from_db()
        self.assertEqual(self.adventure.rollback_min_history_id, entries[2].id)
        self.assertEqual(len(client.prompts), 1)
        self.assertIn("old-post-1", client.prompts[0])
        self.assertIn("old-post-2", client.prompts[0])
        self.assertNotIn("old-post-6", client.prompts[0])

    def test_safety_blocks_high_risk_input(self):
        result = review_text(
            self.adventure,
            "This includes suicide content.",
            user=self.user,
            source="input",
        )
        self.assertEqual(result.action, "block")
        self.assertIn("self_harm", result.categories)

    def test_safety_does_not_treat_offer_to_help_as_help_seeking_warning(self):
        entry = AdventureHistory.objects.create(
            adventure=self.adventure,
            role=AdventureHistory.Role.AI,
            content="Не бойтесь, я помогу вам выбраться из сарая.",
        )

        result = review_text(
            self.adventure,
            entry.content,
            source="output",
            history_entry=entry,
        )

        self.assertEqual(result.action, "allow")
        self.assertFalse(ConsequenceMarker.objects.filter(history_entry=entry).exists())

    @patch("adventures.services.orchestrator.analyze_and_persist_world_confirmation")
    def test_safe_ai_output_does_not_create_safety_review(self, analyze_world):
        entry = AdventureHistory.objects.create(
            adventure=self.adventure,
            role=AdventureHistory.Role.AI,
            content="Mira closes the door and returns to the table.",
        )

        after_ai_turn(self.adventure, entry)

        self.assertFalse(SafetyReview.objects.filter(adventure=self.adventure).exists())
        analyze_world.assert_called_once_with(self.adventure, entry)

    def test_safety_warning_creates_story_consequence_and_prompt_guidance(self):
        entry = AdventureHistory.objects.create(
            adventure=self.adventure,
            role=AdventureHistory.Role.USER,
            content="A classmate starts to bully Mira, and I ask the teacher for help.",
        )

        result = review_text(
            self.adventure,
            entry.content,
            user=self.user,
            source="input",
            history_entry=entry,
            persist=False,
        )
        prompt = _build_generation_prompt(self.adventure, [entry])

        self.assertEqual(result.action, "warn")
        self.assertTrue(
            ConsequenceMarker.objects.filter(
                adventure=self.adventure,
                history_entry=entry,
                kind=ConsequenceMarker.Kind.SAFETY_WARNING,
            ).exists()
        )
        self.assertIn("Safety-sensitive story handling", prompt)
        self.assertIn("bystander support", prompt)

    def test_user_turn_safety_warning_is_stored_once_with_history_entry(self):
        content = "A classmate starts to bully Mira, and I ask the teacher for help."

        result = before_user_turn(self.adventure, self.user, content)
        self.assertEqual(result.action, "warn")
        self.assertFalse(SafetyReview.objects.filter(adventure=self.adventure).exists())

        entry = AdventureHistory.objects.create(
            adventure=self.adventure,
            role=AdventureHistory.Role.USER,
            content=content,
        )
        after_user_turn(self.adventure, self.user, entry)

        reviews = SafetyReview.objects.filter(adventure=self.adventure, action="warn")
        self.assertEqual(reviews.count(), 1)
        self.assertEqual(reviews.get().history_entry, entry)

    def test_growth_objectives_enter_story_prompt_as_narrative_constraints(self):
        objective = LearningObjective.objects.create(
            adventure=self.adventure,
            code="repair",
            title="Repair trust",
            competency="restorative_action",
            weight=5,
        )
        PedagogicalIntervention.objects.create(
            adventure=self.adventure,
            objective=objective,
            kind=PedagogicalIntervention.Kind.REPAIR,
            payload={"constraint": "Open a repair path through NPC trust and visible consequences."},
        )

        prompt = _build_generation_prompt(self.adventure, [])

        self.assertIn("Growth director constraints", prompt)
        self.assertIn("Open a repair path through NPC trust", prompt)
        self.assertIn("Keep growth guidance embedded in the playable scene", prompt)

    def test_story_generation_prompt_uses_story_locale_and_scenario_instructions(self):
        self.adventure.spec_instructions = "Keep the mystery grounded in visible clues."
        self.adventure.save(update_fields=["spec_instructions"])

        prompt = _build_generation_prompt(self.adventure, [])

        self.assertIn("Scenario-specific instructions:", prompt)
        self.assertIn("Keep the mystery grounded in visible clues.", prompt)
        self.assertIn("Write the story continuation in English only.", prompt)
        self.assertNotIn("Сгенерируй следующий абзац", prompt)

    def test_story_generation_prompt_localizes_static_instructions(self):
        cases = (
            ("ru", "Пиши продолжение истории только на русском языке.", "Главные герои не заданы."),
            ("zh-CN", "故事续写只能使用简体中文。", "尚未设置主要角色。"),
        )
        for locale, output_rule, empty_heroes in cases:
            with self.subTest(locale=locale):
                self.adventure.story_locale = locale
                self.adventure.save(update_fields=["story_locale"])

                prompt = _build_generation_prompt(self.adventure, [])

                self.assertIn(output_rule, prompt)
                self.assertIn(empty_heroes, prompt)

    def test_story_generation_prompt_localizes_growth_state_notes(self):
        self.adventure.story_locale = "ru"
        self.adventure.save(update_fields=["story_locale"])
        LearningObjective.objects.create(
            adventure=self.adventure,
            code="repair",
            title="Восстановить доверие",
            competency="restorative_action",
        )
        RepairOpportunity.objects.create(
            adventure=self.adventure,
            competency="restorative_action",
            title="Поговорить с командой",
        )

        prompt = _build_generation_prompt(self.adventure, [])

        self.assertIn("открытый путь исправления: Поговорить с командой", prompt)
        self.assertNotIn("open repair path:", prompt)

    def test_npc_generation_prompt_uses_story_locale_for_json_text_values(self):
        prompt = _build_npc_generation_prompt(self.adventure, [], ["Mira"])

        self.assertIn("NPCs in the party: Mira.", prompt)
        self.assertIn("All JSON text values must be in English only.", prompt)

    def test_generation_prompt_includes_long_horizon_consequence_guidance(self):
        harbor = Location.objects.create(adventure=self.adventure, title="Harbor")
        mira = Character.objects.create(
            adventure=self.adventure,
            title="Mira",
            location=harbor,
            in_party=True,
        )
        apply_narrative_consequence_updates(
            self.adventure,
            [
                {
                    "title": "Mira remembers the lantern repair",
                    "summary": "Mira saw the hero repair the lanterns before leaving.",
                    "importance": 4,
                    "characters": [mira.id],
                    "locations": [harbor.id],
                }
            ],
        )

        prompt = _build_generation_prompt(self.adventure, [])

        self.assertIn("Moral cause-and-effect module (karma)", prompt)
        self.assertIn("Relevant moral cause-and-effect memory", prompt)
        self.assertIn("Mira remembers the lantern repair", prompt)
        self.assertIn('"title": "Mira"', prompt)
        self.assertIn("Make kind, honest, loyal, courageous, and responsible actions", prompt)
        self.assertIn("Make cruelty, exploitation, betrayal, and selfish harm", prompt)
        self.assertIn("do not recursively expand their other memories", prompt)
        self.assertNotIn("Latent goodwill threads", prompt)

    def test_story_modules_are_independently_opt_in(self):
        adventure = Adventure.objects.create(
            author_user=self.user,
            player_user=None,
            template_adventure=None,
            is_template=True,
            title="Plain adventure",
        )
        entry = AdventureHistory.objects.create(
            adventure=adventure,
            role=AdventureHistory.Role.USER,
            content="I walk toward the old gate.",
        )

        analysis = analyze_turn(adventure, entry, client=FakeEvidenceClient("not-json"))
        prompt = _build_generation_prompt(adventure, [entry])

        self.assertEqual(analysis.evidence, [])
        self.assertEqual(analysis.narrative_consequences, [])
        self.assertNotIn("Growth director constraints", prompt)
        self.assertNotIn("Moral cause-and-effect module (karma)", prompt)
        self.assertNotIn("Relevant moral cause-and-effect memory", prompt)

    def test_disabled_modules_are_omitted_from_compaction_prompt(self):
        adventure = Adventure.objects.create(
            author_user=self.user,
            player_user=None,
            template_adventure=None,
            is_template=True,
            title="Plain adventure",
        )

        prompt = _build_card_update_prompt(adventure, [])

        self.assertNotIn('"repair_opportunities"', prompt)
        self.assertNotIn('"consequence_markers"', prompt)
        self.assertNotIn('"narrative_consequences"', prompt)
        self.assertNotIn("Repair opportunities:", prompt)
        self.assertNotIn("Narrative consequences:", prompt)
        self.assertIn("Analyze recent story events and update the state cards.", prompt)

    def test_narrative_only_analysis_omits_growth_schema_and_objectives(self):
        adventure = Adventure.objects.create(
            author_user=self.user,
            player_user=None,
            template_adventure=None,
            is_template=True,
            title="Consequences only",
            narrative_consequences_enabled=True,
        )
        LearningObjective.objects.create(
            adventure=adventure,
            code="hidden-objective",
            title="This objective must not leak",
            competency="empathy",
        )
        entry = AdventureHistory.objects.create(
            adventure=adventure,
            role=AdventureHistory.Role.USER,
            content="I leave a warning for the harbor watch.",
        )
        client = FakeEvidenceClient(
            """
            {
              "evidence": [{
                "competency": "empathy",
                "marker": "ignored",
                "score": 1,
                "confidence": 0.99,
                "excerpt": "leave a warning",
                "rationale": "Ignored because growth analysis is disabled."
              }],
              "repair_opportunities": [{
                "competency": "empathy",
                "title": "Ignored repair"
              }],
              "narrative_consequences": [{
                "title": "Harbor watch warned",
                "summary": "The hero left a warning for the harbor watch.",
                "importance": 2
              }]
            }
            """
        )

        prompt = _build_turn_analysis_prompt(adventure, entry)
        analysis = analyze_turn(adventure, entry, client=client)

        self.assertNotIn('"evidence"', prompt)
        self.assertNotIn('"repair_opportunities"', prompt)
        self.assertNotIn("This objective must not leak", prompt)
        self.assertIn('"narrative_consequences"', prompt)
        self.assertEqual(analysis.evidence, [])
        self.assertEqual(analysis.repair_opportunities, [])
        self.assertEqual(len(analysis.narrative_consequences), 1)

    def test_growth_only_analysis_omits_narrative_schema_and_entity_catalog(self):
        adventure = Adventure.objects.create(
            author_user=self.user,
            player_user=None,
            template_adventure=None,
            is_template=True,
            title="Growth only",
            growth_analysis_enabled=True,
        )
        entry = AdventureHistory.objects.create(
            adventure=adventure,
            role=AdventureHistory.Role.USER,
            content="I ask Mira whether she needs help.",
        )
        LearningObjective.objects.create(
            adventure=adventure,
            code="empathy",
            title="Empathy",
            competency="empathy",
        )
        client = FakeEvidenceClient(
            """
            {
              "evidence": [{
                "competency": "empathy",
                "marker": "asked_about_help",
                "score": 1,
                "confidence": 0.9,
                "excerpt": "ask Mira whether she needs help",
                "rationale": "The action visibly checks whether help is needed."
              }],
              "repair_opportunities": [],
              "narrative_consequences": [{
                "title": "Ignored event",
                "summary": "Ignored because narrative memory is disabled."
              }]
            }
            """
        )

        prompt = _build_turn_analysis_prompt(adventure, entry)
        analysis = analyze_turn(adventure, entry, client=client)

        self.assertIn('"evidence"', prompt)
        self.assertIn('"repair_opportunities"', prompt)
        self.assertNotIn('"narrative_consequences"', prompt)
        self.assertNotIn("Entity catalog:", prompt)
        self.assertEqual(len(analysis.evidence), 1)
        self.assertEqual(analysis.narrative_consequences, [])

    def test_growth_analysis_stays_inactive_without_configured_objectives(self):
        adventure = Adventure.objects.create(
            author_user=self.user,
            player_user=None,
            template_adventure=None,
            is_template=True,
            title="Untargeted growth",
            growth_analysis_enabled=True,
        )
        entry = AdventureHistory.objects.create(
            adventure=adventure,
            role=AdventureHistory.Role.USER,
            content="I ignore Mira and walk away.",
        )
        client = FakeEvidenceClient(
            """
            {
              "evidence": [{
                "competency": "empathy",
                "marker": "ignored_mira",
                "score": -1,
                "confidence": 0.9,
                "excerpt": "ignore Mira",
                "rationale": "The hero walked away."
              }],
              "repair_opportunities": [{
                "competency": "empathy",
                "title": "Talk to Mira later"
              }]
            }
            """
        )

        prompt = _build_turn_analysis_prompt(adventure, entry)
        analysis = analyze_turn(adventure, entry, client=client)

        self.assertNotIn('"evidence"', prompt)
        self.assertNotIn('"repair_opportunities"', prompt)
        self.assertEqual(analysis.evidence, [])
        self.assertEqual(analysis.repair_opportunities, [])

    def test_growth_director_prioritizes_current_repair_state(self):
        empathy = LearningObjective.objects.create(
            adventure=self.adventure,
            code="empathy",
            title="Empathy",
            competency="empathy",
            weight=2,
        )
        inclusion = LearningObjective.objects.create(
            adventure=self.adventure,
            code="inclusion",
            title="Inclusion",
            competency="inclusion",
            weight=1,
        )
        RepairOpportunity.objects.create(
            adventure=self.adventure,
            user=self.user,
            competency="inclusion",
            title="Invite excluded teammate",
        )

        selected = choose_objective(self.adventure)

        self.assertEqual(selected, inclusion)
        self.assertNotEqual(selected, empathy)

    def test_growth_director_handles_active_events_without_description_field(self):
        objective = LearningObjective.objects.create(
            adventure=self.adventure,
            code="cooperation",
            title="Cooperate under pressure",
            competency="cooperation",
            weight=1,
        )
        AdventureEvent.objects.create(
            adventure=self.adventure,
            status=AdventureEvent.Status.ACTIVE,
            title="Team negotiation",
            trigger_hint="The team must cooperate before the harbor gate closes.",
            state="The group is deciding together.",
        )

        selected = choose_objective(self.adventure)

        self.assertEqual(selected, objective)

    def test_choice_cards_follow_state_aware_growth_focus(self):
        empathy = LearningObjective.objects.create(
            adventure=self.adventure,
            code="empathy",
            title="Empathy",
            competency="empathy",
            weight=2,
        )
        inclusion = LearningObjective.objects.create(
            adventure=self.adventure,
            code="inclusion",
            title="Inclusion",
            competency="inclusion",
            weight=1,
        )
        PedagogicalIntervention.objects.create(
            adventure=self.adventure,
            objective=empathy,
            kind=PedagogicalIntervention.Kind.CHOICE_CARDS,
            payload={"cards": ["Ask what the NPC is feeling."]},
        )
        PedagogicalIntervention.objects.create(
            adventure=self.adventure,
            objective=inclusion,
            kind=PedagogicalIntervention.Kind.CHOICE_CARDS,
            payload={"cards": ["Invite the classmate back into the plan."]},
        )
        RepairOpportunity.objects.create(
            adventure=self.adventure,
            user=self.user,
            competency="inclusion",
            title="Classmate left out",
        )

        cards = get_choice_cards(self.adventure, "en")

        self.assertEqual(cards, ["Invite the classmate back into the plan."])

    def test_reflection_prompt_waits_for_meaningful_story_signal(self):
        objective = LearningObjective.objects.create(
            adventure=self.adventure,
            code="empathy",
            title="Empathy",
            competency="empathy",
            weight=5,
        )
        prompt = ReflectionPrompt.objects.create(
            adventure=self.adventure,
            objective=objective,
            question="What might another person feel here?",
        )
        AdventureHistory.objects.create(
            adventure=self.adventure,
            role=AdventureHistory.Role.USER,
            content="I walk down the hallway.",
        )

        self.assertIsNone(choose_reflection_prompt(self.adventure, user=self.user))

        AdventureHistory.objects.create(
            adventure=self.adventure,
            role=AdventureHistory.Role.USER,
            content="I listen and ask what the classmate might feel.",
        )

        self.assertEqual(choose_reflection_prompt(self.adventure, user=self.user), prompt)

    def test_explicit_hero_state_is_formatted_as_self_reported_character_state(self):
        content = format_player_move_content(
            "I ask the group to stop.",
            hero_name="Lin",
            hero_state="angry but trying to stay calm",
        )

        self.assertIn("Lin: I ask the group to stop.", content)
        self.assertIn("явно указано игроком", content)
        self.assertIn("angry but trying to stay calm", content)


class LearningModelTests(TestCase):
    def test_learning_objective_serializer_shape(self):
        User = get_user_model()
        user = User.objects.create_user(username="teacher", password="pass")
        adventure = Adventure.objects.create(
            author_user=user,
            player_user=None,
            template_adventure=None,
            is_template=True,
            title="Template",
        )
        objective = LearningObjective.objects.create(
            adventure=adventure,
            code="empathy",
            title="Empathy",
            competency="empathy",
            weight=3,
        )
        self.assertEqual(objective.competency, "empathy")
        self.assertEqual(objective.weight, 3)

    def test_demo_seed_sets_login_password(self):
        User = get_user_model()

        call_command(
            "seed_education_demo",
            username="seed-teacher",
            password="seed-pass-123",
            verbosity=0,
        )

        user = User.objects.get(username="seed-teacher")
        self.assertTrue(user.check_password("seed-pass-123"))
        template = Adventure.objects.get(
            author_user=user,
            title="Growth-Oriented Demo Scenario",
            is_template=True,
        )
        self.assertEqual(template.story_locale, "en")
        template.story_locale = "ru"
        template.save(update_fields=["story_locale"])

        call_command(
            "seed_education_demo",
            username="seed-teacher",
            password="seed-pass-123",
            verbosity=0,
        )

        template.refresh_from_db()
        self.assertEqual(template.story_locale, "en")

    def test_last_beacon_seed_creates_repeatable_fantasy_demo(self):
        User = get_user_model()

        for _ in range(2):
            call_command(
                "seed_last_beacon_demo",
                username="seed-host",
                password="seed-pass-123",
                verbosity=0,
            )

        user = User.objects.get(username="seed-host")
        self.assertTrue(user.check_password("seed-pass-123"))
        template = Adventure.objects.get(
            author_user=user,
            title="The Last Beacon Pass",
            is_template=True,
        )
        self.assertEqual(template.story_locale, "en")
        self.assertTrue(template.growth_analysis_enabled)
        self.assertTrue(template.narrative_consequences_enabled)
        self.assertEqual(template.locations.count(), 2)
        self.assertEqual(template.characters.count(), 3)
        self.assertEqual(template.skill_systems.count(), 3)
        self.assertEqual(Technique.objects.filter(system__adventure=template).count(), 7)
        self.assertEqual(CharacterSystem.objects.filter(character__adventure=template).count(), 3)
        self.assertEqual(CharacterTechnique.objects.filter(character__adventure=template).count(), 7)
        self.assertEqual(template.learning_objectives.count(), 4)
        self.assertEqual(template.pedagogical_interventions.count(), 3)
        self.assertEqual(template.factions.count(), 1)
        self.assertTrue(
            CharacterFaction.objects.filter(
                character__adventure=template,
                character__title="Raider Pathfinder",
                faction__title="Ashen Pass Raiders",
            ).exists()
        )
        self.assertTrue(
            OtherInfo.objects.filter(
                adventure=template,
                category="mission",
                title="Relight the beacon before dawn",
            ).exists()
        )
        self.assertEqual(template.events.count(), 4)
        self.assertTrue(PublishedAdventure.objects.filter(adventure=template).exists())
        self.assertEqual(
            template.events.get(title="Broken ascent in the sleet").status,
            AdventureEvent.Status.ACTIVE,
        )
        self.assertEqual(
            template.events.get(title="Relight the beacon before dawn").status,
            AdventureEvent.Status.ACTIVE,
        )
        self.assertEqual(
            template.events.get(title="Raider scouts below the pass").status,
            AdventureEvent.Status.ACTIVE,
        )


class LearningApiContractTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.teacher = User.objects.create_user(
            username="teacher",
            email="teacher@example.local",
            password="pass",
        )
        self.student = User.objects.create_user(
            username="student",
            email="student@example.local",
            password="pass",
        )
        self.template = Adventure.objects.create(
            author_user=self.teacher,
            player_user=None,
            template_adventure=None,
            is_template=True,
            title="Template",
            growth_analysis_enabled=True,
            narrative_consequences_enabled=True,
        )
        self.run = Adventure.objects.create(
            author_user=self.teacher,
            player_user=self.student,
            template_adventure=self.template,
            is_template=False,
            title="Run",
            growth_analysis_enabled=True,
            narrative_consequences_enabled=True,
        )
        AdventurePlayer.objects.create(
            adventure=self.run,
            user=self.student,
            slot_number=1,
        )
        self.objective = LearningObjective.objects.create(
            adventure=self.run,
            code="empathy",
            title="Empathy",
            competency="empathy",
            weight=3,
        )
        self.prompt = ReflectionPrompt.objects.create(
            adventure=self.run,
            objective=self.objective,
            question="What might another person feel here?",
        )
        self.client = APIClient()

    def test_pending_reflection_waits_for_user_history(self):
        self.client.force_authenticate(user=self.student)
        url = f"/api/adventures/runs/{self.run.id}/debriefs/pending/"

        before_response = self.client.get(url)
        self.assertEqual(before_response.status_code, 200)
        self.assertIsNone(before_response.data["prompt"])

        AdventureHistory.objects.create(
            adventure=self.run,
            role=AdventureHistory.Role.USER,
            content="I listen and ask how the classmate feels.",
        )
        after_response = self.client.get(url)
        self.assertEqual(after_response.status_code, 200)
        self.assertEqual(after_response.data["prompt"]["id"], self.prompt.id)

    @patch("adventures.views.learning_views.extract_observable_evidence")
    def test_debrief_evidence_is_limited_to_active_objectives(self, extract_evidence):
        extract_evidence.return_value = [
            EvidenceItem(
                competency="empathy",
                marker="listened",
                score=1,
                confidence=0.9,
                excerpt="I listened",
            ),
            EvidenceItem(
                competency="inclusion",
                marker="unexpected",
                score=1,
                confidence=0.9,
                excerpt="I listened",
            ),
        ]
        self.client.force_authenticate(user=self.student)

        response = self.client.post(
            f"/api/adventures/runs/{self.run.id}/debriefs/{self.prompt.id}/responses/",
            {"content": "I listened"},
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            list(
                BehaviorEvidence.objects.filter(adventure=self.run).values_list(
                    "competency",
                    flat=True,
                )
            ),
            ["empathy"],
        )

    def test_player_profile_alias_is_primary_profile_route(self):
        self.client.force_authenticate(user=self.student)

        update_response = self.client.put(
            "/api/player/profile/",
            {"age_band": "18+", "consent_confirmed": True},
            format="json",
        )
        self.assertEqual(update_response.status_code, 200)
        self.assertEqual(update_response.data["age_band"], "18+")
        self.assertTrue(update_response.data["consent_confirmed"])

        legacy_response = self.client.get("/api/learner/profile/")
        self.assertEqual(legacy_response.status_code, 200)
        self.assertEqual(legacy_response.data["age_band"], "18+")

    def test_growth_and_debrief_aliases_match_corrected_product_language(self):
        self.client.force_authenticate(user=self.student)
        AdventureHistory.objects.create(
            adventure=self.run,
            role=AdventureHistory.Role.USER,
            content=(
                "Hero: I ask the team to pause.\n"
                "Состояние/намерение героя (явно указано игроком): worried but determined"
            ),
            metadata={"hero_state": "worried but determined"},
        )
        evidence = BehaviorEvidence.objects.create(
            adventure=self.run,
            user=self.student,
            competency="empathy",
            marker="empathy_growth_opportunity",
            score=-1,
            excerpt="ignored a teammate",
        )
        RepairOpportunity.objects.create(
            adventure=self.run,
            user=self.student,
            source_evidence=evidence,
            competency="empathy",
            title="Empathy repair opportunity",
            suggested_action="Invite the teammate back into the scene.",
        )
        ConsequenceMarker.objects.create(
            adventure=self.run,
            user=self.student,
            evidence=evidence,
            competency="empathy",
            kind=ConsequenceMarker.Kind.REPAIR_OPENED,
            title="Repair path opened",
            weight=-1,
        )

        growth_response = self.client.get(f"/api/adventures/runs/{self.run.id}/growth/summary/")
        debrief_response = self.client.get(
            f"/api/adventures/runs/{self.run.id}/debriefs/pending/"
        )

        self.assertEqual(growth_response.status_code, 200)
        self.assertNotIn("objectives", growth_response.data)
        self.assertNotIn("repair_opportunities", growth_response.data)
        self.assertNotIn("consequence_markers", growth_response.data)
        self.assertNotIn("latest_evidence", growth_response.data)
        self.assertEqual(debrief_response.status_code, 200)
        self.assertEqual(debrief_response.data["prompt"]["id"], self.prompt.id)

    def test_gm_dashboard_is_not_visible_to_player_owner(self):
        self.client.force_authenticate(user=self.student)
        response = self.client.get(f"/api/adventures/runs/{self.run.id}/gm/dashboard/")
        self.assertEqual(response.status_code, 403)

        self.client.force_authenticate(user=self.teacher)
        gm_response = self.client.get(
            f"/api/adventures/runs/{self.run.id}/gm/dashboard/"
        )
        self.assertEqual(gm_response.status_code, 200)
        self.assertIn("story_settings", gm_response.data)
        self.assertNotIn("privacy_notice", gm_response.data)

    def test_gm_controls_shared_story_settings(self):
        self.client.force_authenticate(user=self.student)
        student_response = self.client.put(
            f"/api/adventures/runs/{self.run.id}/gm/dashboard/",
            {
                "facilitator_enabled": False,
                "story_locale": "zh-CN",
                "story_simple_language": True,
                "story_reduced_text_length": True,
                "growth_analysis_enabled": False,
                "narrative_consequences_enabled": False,
            },
            format="json",
        )
        self.assertEqual(student_response.status_code, 403)

        self.client.force_authenticate(user=self.teacher)
        gm_response = self.client.put(
            f"/api/adventures/runs/{self.run.id}/gm/dashboard/",
            {
                "facilitator_enabled": False,
                "story_locale": "zh-CN",
                "story_simple_language": True,
                "story_reduced_text_length": True,
                "growth_analysis_enabled": False,
                "narrative_consequences_enabled": False,
            },
            format="json",
        )
        self.assertEqual(gm_response.status_code, 200)
        self.run.refresh_from_db()
        self.assertFalse(self.run.facilitator_enabled)
        self.assertEqual(self.run.story_locale, "zh-CN")
        self.assertTrue(self.run.story_simple_language)
        self.assertTrue(self.run.story_reduced_text_length)
        self.assertFalse(self.run.growth_analysis_enabled)
        self.assertFalse(self.run.narrative_consequences_enabled)

        disabled_response = self.client.get(
            f"/api/adventures/runs/{self.run.id}/gm/dashboard/"
        )
        self.assertEqual(disabled_response.status_code, 403)

    def test_portfolio_export_scope_matches_viewer_role(self):
        User = get_user_model()
        other_student = User.objects.create_user(
            username="other-student",
            email="other-student@example.local",
            password="pass",
        )
        AdventurePlayer.objects.create(
            adventure=self.run,
            user=other_student,
            slot_number=2,
        )
        first_response = ReflectionResponse.objects.create(
            adventure=self.run,
            user=self.student,
            prompt=self.prompt,
            content="My private reflection about asking for help.",
        )
        ReflectionResponse.objects.create(
            adventure=self.run,
            user=other_student,
            prompt=self.prompt,
            content="Other learner private reflection.",
        )
        BehaviorEvidence.objects.create(
            adventure=self.run,
            user=self.student,
            reflection_response=first_response,
            competency="help_seeking",
            marker="help_seeking_observed",
            score=1,
            excerpt="asking for help",
        )
        RepairOpportunity.objects.create(
            adventure=self.run,
            user=self.student,
            competency="help_seeking",
            title="Help-seeking repair opportunity",
        )
        ConsequenceMarker.objects.create(
            adventure=self.run,
            user=self.student,
            competency="help_seeking",
            kind=ConsequenceMarker.Kind.CONSTRUCTIVE_CHOICE,
            title="Asked for help",
            weight=1,
        )

        self.client.force_authenticate(user=self.student)
        learner_response = self.client.get(
            f"/api/adventures/runs/{self.run.id}/portfolio/export/"
        )
        self.assertEqual(learner_response.status_code, 200)
        self.assertEqual(learner_response.json()["scope"], "learner")
        self.assertNotIn("privacy_notice", learner_response.json())
        learner_payload = learner_response.content.decode("utf-8")
        self.assertIn("My private reflection", learner_payload)
        self.assertIn("Help-seeking repair opportunity", learner_payload)
        self.assertIn("Asked for help", learner_payload)
        self.assertNotIn("Other learner private reflection", learner_payload)

        self.client.force_authenticate(user=self.teacher)
        teacher_response = self.client.get(
            f"/api/adventures/runs/{self.run.id}/portfolio/export/"
        )
        self.assertEqual(teacher_response.status_code, 200)
        teacher_payload = teacher_response.json()
        self.assertEqual(teacher_payload["scope"], "run")
        self.assertNotIn("privacy_notice", teacher_payload)
        self.assertEqual(teacher_payload["learner_count"], 2)

    def test_template_export_import_preserves_learning_pack(self):
        self.template.story_locale = "zh-CN"
        self.template.story_simple_language = True
        self.template.story_reduced_text_length = True
        self.template.facilitator_enabled = False
        self.template.growth_analysis_enabled = True
        self.template.narrative_consequences_enabled = True
        self.template.save(
            update_fields=[
                "facilitator_enabled",
                "story_locale",
                "story_simple_language",
                "story_reduced_text_length",
                "growth_analysis_enabled",
                "narrative_consequences_enabled",
            ]
        )
        template_objective = LearningObjective.objects.create(
            adventure=self.template,
            code="team-responsibility",
            title="Shared responsibility",
            competency="cooperation",
            weight=4,
        )
        ReflectionPrompt.objects.create(
            adventure=self.template,
            objective=template_objective,
            question="How could the team make the decision together?",
        )
        PedagogicalIntervention.objects.create(
            adventure=self.template,
            objective=template_objective,
            kind=PedagogicalIntervention.Kind.CHOICE_CARDS,
            payload={"cards": ["Pause and ask each teammate for one concern."]},
        )
        Character.objects.create(
            adventure=self.template,
            title="Template guide",
        )
        self.client.force_authenticate(user=self.teacher)

        export_response = self.client.get(f"/api/adventures/templates/{self.template.id}/export/")
        self.assertEqual(export_response.status_code, 200)
        payload = export_response.data
        self.assertEqual(payload["version"], 5)
        self.assertFalse(payload["adventure"]["facilitator_enabled"])
        self.assertEqual(payload["adventure"]["story_locale"], "zh-CN")
        self.assertTrue(payload["adventure"]["story_simple_language"])
        self.assertTrue(payload["adventure"]["story_reduced_text_length"])
        self.assertTrue(payload["adventure"]["growth_analysis_enabled"])
        self.assertTrue(payload["adventure"]["narrative_consequences_enabled"])
        self.assertEqual(len(payload["learning_objectives"]), 1)
        self.assertEqual(len(payload["reflection_prompts"]), 1)
        self.assertEqual(len(payload["pedagogical_interventions"]), 1)
        payload["characters"][0]["story_status"] = "unknown"

        import_response = self.client.post(
            "/api/adventures/templates/import/",
            payload,
            format="json",
        )
        self.assertEqual(import_response.status_code, 201)
        imported_id = import_response.data["id"]
        imported_template = Adventure.objects.get(id=imported_id)
        self.assertFalse(imported_template.facilitator_enabled)
        self.assertEqual(imported_template.story_locale, "zh-CN")
        self.assertTrue(imported_template.story_simple_language)
        self.assertTrue(imported_template.story_reduced_text_length)
        self.assertTrue(imported_template.growth_analysis_enabled)
        self.assertTrue(imported_template.narrative_consequences_enabled)
        imported_objective = LearningObjective.objects.get(
            adventure_id=imported_id,
            code="team-responsibility",
        )
        self.assertEqual(imported_objective.competency, "cooperation")
        self.assertTrue(
            ReflectionPrompt.objects.filter(
                adventure_id=imported_id,
                objective=imported_objective,
            ).exists()
        )
        imported_intervention = PedagogicalIntervention.objects.get(
            adventure_id=imported_id,
            objective=imported_objective,
        )
        self.assertEqual(
            imported_intervention.payload["cards"],
            ["Pause and ask each teammate for one concern."],
        )
        self.assertEqual(
            Character.objects.get(
                adventure=imported_template,
                title="Template guide",
            ).story_status,
            Character.StoryStatus.ACTIVE,
        )

    @patch.dict("os.environ", {"TEMPLATE_TRANSLATION_BATCH_MAX_ITEMS": "2"})
    @patch("adventures.views.transfer_views.get_llm_client")
    def test_template_translation_creates_independent_batched_clone(self, get_llm_client):
        translation_client = FakeTemplateTranslationClient()
        get_llm_client.return_value = translation_client
        self.template.description = "A complete template"
        self.template.intro = "Welcome, <main_hero>."
        self.template.spec_instructions = "Keep the mystery."
        self.template.save(update_fields=["description", "intro", "spec_instructions"])
        location = Location.objects.create(
            adventure=self.template,
            title="Library",
            description="A quiet hall",
            tags=["safe-zone"],
        )
        race = Race.objects.create(
            adventure=self.template,
            title="Human",
            description="A regular person",
        )
        faction = Faction.objects.create(
            adventure=self.template,
            title="Archivists",
            description="They protect knowledge",
        )
        system = SkillSystem.objects.create(
            adventure=self.template,
            title="Investigation",
            description="Notice useful details",
            w_mind=100,
            formula_hint="Mind + 1",
        )
        technique = Technique.objects.create(
            system=system,
            title="Careful search",
            description="Look behind the obvious clue",
            tier=None,
        )
        guide = Character.objects.create(
            adventure=self.template,
            race=race,
            location=location,
            title="Guide",
            description="Knows where to look",
            tags=["mentor"],
        )
        learner = Character.objects.create(
            adventure=self.template,
            race=race,
            location=location,
            title="Learner",
            description="Needs a clue",
        )
        CharacterSystem.objects.create(
            character=guide,
            system=system,
            level=2,
            notes="Experienced investigator",
        )
        CharacterTechnique.objects.create(
            character=guide,
            technique=technique,
            notes="Use only when needed",
        )
        CharacterFaction.objects.create(character=guide, faction=faction)
        CharacterRelationship.objects.create(
            from_character=guide,
            to_character=learner,
            kind="mentor",
            description="Wants the learner to succeed",
        )
        objective = LearningObjective.objects.create(
            adventure=self.template,
            code="cooperate",
            title="Work together",
            description="Ask for another perspective",
            competency="cooperation",
        )
        ReflectionPrompt.objects.create(
            adventure=self.template,
            objective=objective,
            question="Whose perspective could help?",
        )
        PedagogicalIntervention.objects.create(
            adventure=self.template,
            objective=objective,
            kind=PedagogicalIntervention.Kind.CHOICE_CARDS,
            payload={"cards": ["Ask the guide for one clue."], "limit": 1},
        )
        AdventureHeroSetup.objects.create(
            adventure=self.template,
            default_location=location,
            require_race=False,
            default_race=race,
            require_age=False,
            default_age=16,
        )
        self.template.shared_location = location
        self.template.primary_hero = guide
        self.template.save(update_fields=["shared_location", "primary_hero"])
        self.template.primary_heroes.set([guide])
        template_count = Adventure.objects.filter(is_template=True).count()
        self.client.force_authenticate(user=self.teacher)

        response = self.client.post(
            f"/api/adventures/templates/{self.template.id}/translate/",
            {"target_locale": "ru"},
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.data["can_edit"])
        self.assertGreater(response.data["translation"]["batches"], 1)
        self.assertEqual(
            response.data["translation"]["batches"],
            len(translation_client.prompts),
        )
        self.assertEqual(
            Adventure.objects.filter(is_template=True).count(),
            template_count + 1,
        )
        copied = Adventure.objects.get(id=response.data["id"])
        self.assertEqual(copied.title, "translated::Template")
        self.assertEqual(copied.story_locale, "ru")
        copied_location = Location.objects.get(adventure=copied)
        self.assertEqual(copied_location.title, "translated::Library")
        self.assertEqual(copied_location.tags, ["safe-zone"])
        copied_guide = Character.objects.get(adventure=copied, title="translated::Guide")
        copied_learner = Character.objects.get(adventure=copied, title="translated::Learner")
        copied_faction = Faction.objects.get(adventure=copied)
        copied_system = SkillSystem.objects.get(adventure=copied)
        copied_technique = Technique.objects.get(system=copied_system)
        self.assertTrue(
            CharacterSystem.objects.filter(
                character=copied_guide,
                system=copied_system,
                notes="translated::Experienced investigator",
            ).exists()
        )
        self.assertTrue(
            CharacterTechnique.objects.filter(
                character=copied_guide,
                technique=copied_technique,
                notes="translated::Use only when needed",
            ).exists()
        )
        self.assertTrue(
            CharacterFaction.objects.filter(
                character=copied_guide,
                faction=copied_faction,
            ).exists()
        )
        copied_relationship = CharacterRelationship.objects.get(
            from_character=copied_guide,
            to_character=copied_learner,
        )
        self.assertEqual(
            copied_relationship.description,
            "translated::Wants the learner to succeed",
        )
        copied_intervention = PedagogicalIntervention.objects.get(adventure=copied)
        self.assertEqual(
            copied_intervention.payload,
            {"cards": ["translated::Ask the guide for one clue."], "limit": 1},
        )
        copied_setup = AdventureHeroSetup.objects.get(adventure=copied)
        self.assertEqual(copied_setup.default_location, copied_location)
        self.assertEqual(copied_setup.default_race.adventure, copied)
        self.assertEqual(copied.shared_location, copied_location)
        self.assertEqual(copied.primary_hero, copied_guide)
        self.assertEqual(list(copied.primary_heroes.all()), [copied_guide])
        self.template.refresh_from_db()
        self.assertEqual(self.template.title, "Template")
        self.assertEqual(self.template.story_locale, "en")

    @patch("adventures.views.transfer_views.get_llm_client")
    def test_template_translation_does_not_create_partial_copy_for_invalid_json(
        self,
        get_llm_client,
    ):
        get_llm_client.return_value = FakeEvidenceClient("not-json")
        template_count = Adventure.objects.filter(is_template=True).count()
        self.client.force_authenticate(user=self.teacher)

        response = self.client.post(
            f"/api/adventures/templates/{self.template.id}/translate/",
            {"target_locale": "ru"},
            format="json",
        )

        self.assertEqual(response.status_code, 502)
        self.assertEqual(
            Adventure.objects.filter(is_template=True).count(),
            template_count,
        )

    def test_growth_layer_crud_is_editable_on_template(self):
        self.client.force_authenticate(user=self.teacher)
        objective_response = self.client.post(
            f"/api/adventures/templates/{self.template.id}/learning-objectives/",
            {
                "code": "repair",
                "title": "Repair trust",
                "description": "Create visible chances to rebuild trust.",
                "competency": "restorative_action",
                "weight": 3,
                "is_active": True,
            },
            format="json",
        )
        self.assertEqual(objective_response.status_code, 201)
        objective_id = objective_response.data["id"]

        prompt_response = self.client.post(
            f"/api/adventures/templates/{self.template.id}/reflection-prompts/",
            {
                "objective": objective_id,
                "trigger_kind": "key_choice",
                "question": "What could repair trust in the scene?",
                "is_active": True,
            },
            format="json",
        )
        self.assertEqual(prompt_response.status_code, 201)
        self.assertEqual(prompt_response.data["objective"]["id"], objective_id)

        intervention_response = self.client.post(
            f"/api/adventures/templates/{self.template.id}/pedagogical-interventions/",
            {
                "objective": objective_id,
                "kind": "choice_cards",
                "payload": {"cards": ["Ask what would help repair trust."]},
                "is_active": True,
            },
            format="json",
        )
        self.assertEqual(intervention_response.status_code, 201)
        self.assertEqual(intervention_response.data["objective"], objective_id)
        self.assertEqual(
            intervention_response.data["payload"]["cards"],
            ["Ask what would help repair trust."],
        )

        objective_update_response = self.client.put(
            f"/api/adventures/templates/{self.template.id}/learning-objectives/{objective_id}/",
            {
                "code": "repair",
                "title": "Repair trust",
                "description": "Updated repair arc.",
                "competency": "restorative_action",
                "weight": 5,
                "is_active": True,
            },
            format="json",
        )
        self.assertEqual(objective_update_response.status_code, 200)
        self.assertEqual(objective_update_response.data["weight"], 5)

    def test_starting_template_copies_learning_pack_to_run(self):
        self.template.story_locale = "zh-CN"
        self.template.story_simple_language = True
        self.template.story_reduced_text_length = True
        self.template.facilitator_enabled = False
        self.template.growth_analysis_enabled = True
        self.template.narrative_consequences_enabled = True
        self.template.save(
            update_fields=[
                "facilitator_enabled",
                "story_locale",
                "story_simple_language",
                "story_reduced_text_length",
                "growth_analysis_enabled",
                "narrative_consequences_enabled",
            ]
        )
        template_objective = LearningObjective.objects.create(
            adventure=self.template,
            code="include-classmate",
            title="Include a classmate",
            competency="inclusion",
            weight=5,
        )
        ReflectionPrompt.objects.create(
            adventure=self.template,
            objective=template_objective,
            question="What accommodation would help everyone participate?",
        )
        PedagogicalIntervention.objects.create(
            adventure=self.template,
            objective=template_objective,
            kind=PedagogicalIntervention.Kind.CHOICE_CARDS,
            payload={"cards": ["Move the noisy task outside."]},
        )
        self.client.force_authenticate(user=self.teacher)

        response = self.client.post(f"/api/adventures/templates/{self.template.id}/start/")

        self.assertEqual(response.status_code, 201)
        run_id = response.data["id"]
        run = Adventure.objects.get(id=run_id)
        self.assertFalse(run.facilitator_enabled)
        self.assertEqual(run.story_locale, "zh-CN")
        self.assertTrue(run.story_simple_language)
        self.assertTrue(run.story_reduced_text_length)
        self.assertTrue(run.growth_analysis_enabled)
        self.assertTrue(run.narrative_consequences_enabled)
        copied_objective = LearningObjective.objects.get(
            adventure_id=run_id,
            code="include-classmate",
        )
        self.assertEqual(copied_objective.competency, "inclusion")
        self.assertTrue(
            ReflectionPrompt.objects.filter(
                adventure_id=run_id,
                objective=copied_objective,
            ).exists()
        )
        self.assertTrue(
            PedagogicalIntervention.objects.filter(
                adventure_id=run_id,
                objective=copied_objective,
                kind=PedagogicalIntervention.Kind.CHOICE_CARDS,
            ).exists()
        )
