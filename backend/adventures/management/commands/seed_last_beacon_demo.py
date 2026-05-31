"""Create the entertainment-first fantasy scenario used in the contest video."""
from __future__ import annotations

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from adventures.models import (
    Adventure,
    AdventureEvent,
    AdventureHeroSetup,
    Character,
    CharacterFaction,
    Faction,
    CharacterSystem,
    CharacterTechnique,
    LearningObjective,
    Location,
    OtherInfo,
    PedagogicalIntervention,
    PublishedAdventure,
    Race,
    ReflectionPrompt,
    SkillSystem,
    Technique,
)


class Command(BaseCommand):
    help = "Seed The Last Beacon Pass fantasy demo scenario."

    def add_arguments(self, parser):
        parser.add_argument("--username", default="demo_host")
        parser.add_argument(
            "--password",
            default="demo12345",
            help="Password to set for the local demo host account.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        User = get_user_model()
        username = options["username"]
        password = options["password"]
        user, user_created = User.objects.get_or_create(
            username=username,
            defaults={"email": f"{username}@example.local"},
        )
        if password:
            user.set_password(password)
            user.save(update_fields=["password"])

        template, template_created = Adventure.objects.update_or_create(
            author_user=user,
            is_template=True,
            player_user=None,
            template_adventure=None,
            title="The Last Beacon Pass",
            defaults={
                "description": (
                    "A tense heroic fantasy adventure. The mountain beacon guarding Ashen Pass "
                    "has gone dark in a sleet storm. Before dawn, raiders will test the border road."
                ),
                "intro": (
                    "<main_hero> climbs Ashen Pass with Mara, a young ranger who knows the old "
                    "tower paths. The mountain beacon has gone dark in a sleet storm. Before dawn, "
                    "raiders will test the border road. Mara has never forgiven herself for "
                    "failing her captain in this same place three winters ago."
                ),
                "spec_instructions": (
                    "This must feel like a tense heroic fantasy adventure, not therapy or a lesson. "
                    "Keep NPC reactions dramatic and diegetic. If the player treats Mara with "
                    "trust, asks for her knowledge, shares the burden, or repairs tension after a "
                    "harsh exchange, later scenes may open a hidden maintenance route, stronger "
                    "cooperation, and a more elegant way to relight the beacon. If the player "
                    "pressures, humiliates, or ignores her, keep the story fully playable but make "
                    "the path colder, costlier, and less cooperative. Avoid explicit moral scores, "
                    "diagnoses, personality labels, and didactic narration. Show consequences "
                    "through trust, access, risk, duty, and world response. Never narrate unspoken "
                    "thoughts, feelings, or motives for the player character. Do not repeat the same "
                    "storm, climbing, or urgency description unless the situation changes. Every "
                    "continuation must materially advance the route, the raider threat, or the "
                    "beacon mission. Do not reveal the hidden maintenance entrance after the first "
                    "polite request: reveal a clue first, then let trust, cooperation, and Mara's "
                    "Read the Old Stone technique make the entrance available in a later scene."
                ),
                "story_locale": Adventure.StoryLocale.EN,
                "facilitator_enabled": True,
                "growth_analysis_enabled": True,
                "narrative_consequences_enabled": True,
            },
        )

        trail, _ = Location.objects.update_or_create(
            adventure=template,
            title="Ashen Pass Trail",
            defaults={
                "description": (
                    "A storm-lashed mountain path below the old beacon tower. Ice, loose stone, "
                    "and a broken ascent make every choice costly."
                ),
                "x": 0,
                "y": 0,
                "tags": ["fantasy", "mountain", "storm", "border"],
            },
        )
        tower, _ = Location.objects.update_or_create(
            adventure=template,
            title="Old Beacon Tower",
            defaults={
                "description": (
                    "A weather-beaten border tower above the pass. Its main stair is exposed, but "
                    "an old maintenance route may still connect the lower galleries to the beacon."
                ),
                "x": 1,
                "y": 1,
                "tags": ["fantasy", "tower", "beacon", "hidden-route"],
            },
        )
        race, _ = Race.objects.update_or_create(
            adventure=template,
            title="Human",
            defaults={
                "description": "A human traveler of the borderlands.",
                "tags": ["player"],
            },
        )
        hero, _ = Character.objects.update_or_create(
            adventure=template,
            title="Border Warden",
            defaults={
                "race": race,
                "location": trail,
                "is_player": True,
                "in_party": True,
                "age": 30,
                "body_power": 2,
                "mind_power": 2,
                "will_power": 2,
                "description": (
                    "A border warden responsible for relighting the beacon before raiders reach "
                    "Ashen Pass. The warden must decide how to lead under pressure."
                ),
                "tags": ["player", "warden", "border"],
            },
        )
        mara, _ = Character.objects.update_or_create(
            adventure=template,
            title="Mara",
            defaults={
                "race": race,
                "location": trail,
                "is_player": False,
                "in_party": True,
                "age": 27,
                "body_power": 2,
                "mind_power": 2,
                "will_power": 2,
                "description": (
                    "A young ranger who knows the old tower paths. Three winters ago, her captain "
                    "died after she failed to reach the beacon in time. She is capable and guarded, "
                    "not fragile: trust, pressure, and repair should affect her cooperation."
                ),
                "tags": ["npc", "ranger", "companion", "mara"],
            },
        )
        template.primary_heroes.set([hero])
        template.primary_hero = hero
        template.shared_location = trail
        template.save(update_fields=["primary_hero", "shared_location", "updated_at"])
        AdventureHeroSetup.objects.update_or_create(
            adventure=template,
            defaults={
                "default_location": trail,
                "require_race": False,
                "default_race": race,
                "require_age": False,
                "default_age": 30,
                "require_body_power": False,
                "default_body_power": 2,
                "require_mind_power": False,
                "default_mind_power": 2,
                "require_will_power": False,
                "default_will_power": 2,
            },
        )

        systems = [
            (
                "Border Warden Arms",
                {
                    "description": (
                        "Defensive martial training for holding mountain roads, protecting "
                        "companions, and controlling narrow ground under pressure."
                    ),
                    "tags": ["martial", "defense", "warden"],
                    "w_body": 3,
                    "w_mind": 1,
                    "w_will": 2,
                    "formula_hint": "Rewards disciplined positioning, protection, and control.",
                },
            ),
            (
                "Ranger Fieldcraft",
                {
                    "description": (
                        "Mountain-ranger expertise in archery, storm travel, tracking, and reading "
                        "old routes through dangerous terrain."
                    ),
                    "tags": ["ranger", "archery", "survival", "traversal"],
                    "w_body": 2,
                    "w_mind": 3,
                    "w_will": 1,
                    "formula_hint": "Rewards observation, mobility, and preparation.",
                },
            ),
            (
                "Beaconfire Magic",
                {
                    "description": (
                        "Old border magic used to kindle signal flames and raise brief protective "
                        "wards against storm, darkness, and attack."
                    ),
                    "tags": ["magic", "fire", "ward", "beacon"],
                    "w_body": 0,
                    "w_mind": 2,
                    "w_will": 3,
                    "formula_hint": "Rewards focus and resolve; beacon-scale effects require preparation.",
                },
            ),
        ]
        system_map = {}
        for title, defaults in systems:
            system_map[title], _ = SkillSystem.objects.update_or_create(
                adventure=template,
                title=title,
                defaults=defaults,
            )

        techniques = [
            (
                "Border Warden Arms",
                "Shield-Line Stance",
                {
                    "description": (
                        "Brace behind shield and terrain to protect a companion while holding a "
                        "narrow approach."
                    ),
                    "tags": ["martial", "defense", "shield"],
                    "difficulty": 2,
                    "tier": 1,
                    "required_system_level": 1,
                },
            ),
            (
                "Border Warden Arms",
                "Hook and Disarm",
                {
                    "description": (
                        "Catch an opponent's weapon or limb with a hooked polearm and force an "
                        "opening without relying on a killing blow."
                    ),
                    "tags": ["martial", "control", "polearm"],
                    "difficulty": 3,
                    "tier": 1,
                    "required_system_level": 2,
                },
            ),
            (
                "Ranger Fieldcraft",
                "Surefoot Traverse",
                {
                    "description": (
                        "Find a stable line across ice, loose stone, or broken masonry and guide "
                        "another traveler through it."
                    ),
                    "tags": ["ranger", "traversal", "support"],
                    "difficulty": 2,
                    "tier": 1,
                    "required_system_level": 1,
                },
            ),
            (
                "Ranger Fieldcraft",
                "Stormline Shot",
                {
                    "description": (
                        "Loose a controlled bow shot through wind and sleet to pin down a threat "
                        "or break exposed equipment."
                    ),
                    "tags": ["ranger", "archery", "combat"],
                    "difficulty": 3,
                    "tier": 1,
                    "required_system_level": 2,
                },
            ),
            (
                "Ranger Fieldcraft",
                "Read the Old Stone",
                {
                    "description": (
                        "Recognize old masonry seams, maintenance passages, and safer approaches "
                        "hidden by weather or collapse."
                    ),
                    "tags": ["ranger", "observation", "hidden-route"],
                    "difficulty": 3,
                    "tier": 1,
                    "required_system_level": 2,
                },
            ),
            (
                "Beaconfire Magic",
                "Ember Ward",
                {
                    "description": (
                        "Raise a brief circle of warm sparks that blunts wind, darkness, and the "
                        "first force of an incoming attack."
                    ),
                    "tags": ["magic", "ward", "defense"],
                    "difficulty": 2,
                    "tier": 1,
                    "required_system_level": 1,
                },
            ),
            (
                "Beaconfire Magic",
                "Beacon Spark",
                {
                    "description": (
                        "Kindle a focused magical flame capable of igniting prepared signal fuel "
                        "even in severe wind and sleet."
                    ),
                    "tags": ["magic", "fire", "beacon"],
                    "difficulty": 3,
                    "tier": 1,
                    "required_system_level": 2,
                },
            ),
        ]
        technique_map = {}
        for system_title, title, defaults in techniques:
            technique_map[title], _ = Technique.objects.update_or_create(
                system=system_map[system_title],
                title=title,
                defaults=defaults,
            )

        character_systems = [
            (hero, "Border Warden Arms", 2, "Trained to hold exposed border roads."),
            (hero, "Beaconfire Magic", 2, "Sworn to maintain and relight the pass beacons."),
            (mara, "Ranger Fieldcraft", 3, "Experienced in storm travel and old tower routes."),
        ]
        for character, system_title, level, notes in character_systems:
            CharacterSystem.objects.update_or_create(
                character=character,
                system=system_map[system_title],
                defaults={"level": level, "progress_percent": 0, "notes": notes},
            )

        character_techniques = [
            (hero, "Shield-Line Stance"),
            (hero, "Hook and Disarm"),
            (hero, "Ember Ward"),
            (hero, "Beacon Spark"),
            (mara, "Surefoot Traverse"),
            (mara, "Stormline Shot"),
            (mara, "Read the Old Stone"),
        ]
        for character, technique_title in character_techniques:
            CharacterTechnique.objects.update_or_create(
                character=character,
                technique=technique_map[technique_title],
                defaults={"notes": "Available at the start of The Last Beacon Pass."},
            )

        raiders, _ = Faction.objects.update_or_create(
            adventure=template,
            title="Ashen Pass Raiders",
            defaults={
                "description": (
                    "A mobile raiding force probing the border road before dawn. Their scouts are "
                    "already climbing through the storm below the beacon tower."
                ),
                "tags": ["raiders", "hostile", "border-threat"],
            },
        )
        scout, _ = Character.objects.update_or_create(
            adventure=template,
            title="Raider Pathfinder",
            defaults={
                "race": race,
                "location": trail,
                "is_player": False,
                "in_party": False,
                "age": 34,
                "body_power": 2,
                "mind_power": 1,
                "will_power": 1,
                "description": (
                    "An advance scout climbing toward the tower below the party. His shuttered "
                    "lantern flashes through the sleet, and he is trying to mark a route for the "
                    "raiders behind him. He creates immediate external pressure without replacing "
                    "the beacon mission."
                ),
                "tags": ["npc", "hostile", "raider", "scout"],
            },
        )
        CharacterFaction.objects.update_or_create(character=scout, faction=raiders)
        OtherInfo.objects.update_or_create(
            adventure=template,
            category="mission",
            title="Relight the beacon before dawn",
            defaults={
                "description": (
                    "Reach the Old Beacon Tower, repair the storm-damaged signal fire, and relight "
                    "it before raider scouts secure the pass. The storm and the scouts must create "
                    "active pressure: the story should not stall in repeated climbing scenes."
                ),
                "tags": ["mission", "beacon", "deadline", "raiders"],
            },
        )

        objectives = [
            (
                "share-agency",
                "Trust and shared agency under pressure",
                "cooperation",
                5,
                "Notice opportunities to ask for Mara's knowledge, share the burden, and leave "
                "room for her agency without presenting one mandatory answer.",
            ),
            (
                "seek-guidance",
                "Ask for help when the path is uncertain",
                "help_seeking",
                4,
                "Notice opportunities to seek practical help or local knowledge instead of "
                "treating pressure as a reason to act alone.",
            ),
            (
                "repair-tension",
                "Repair trust after a harsh exchange",
                "restorative_action",
                4,
                "If trust is damaged, keep an in-world path open for acknowledgement, repair, "
                "and renewed cooperation.",
            ),
            (
                "perspective-under-pressure",
                "Take another perspective under pressure",
                "empathy",
                3,
                "Allow the story to reveal useful context when the player listens without "
                "diagnosing Mara or turning the scene into a lesson.",
            ),
        ]
        objective_map = {}
        for code, title, competency, weight, description in objectives:
            objective_map[code], _ = LearningObjective.objects.update_or_create(
                adventure=template,
                code=code,
                defaults={
                    "title": title,
                    "competency": competency,
                    "weight": weight,
                    "description": description,
                    "is_active": True,
                },
            )

        ReflectionPrompt.objects.update_or_create(
            adventure=template,
            objective=objective_map["repair-tension"],
            question="Field journal: if the exchange with Mara became tense, what could rebuild trust before the final climb?",
            defaults={"is_active": True},
        )
        PedagogicalIntervention.objects.update_or_create(
            adventure=template,
            objective=objective_map["share-agency"],
            kind=PedagogicalIntervention.Kind.PERSPECTIVE,
            defaults={
                "payload": {
                    "constraint": (
                        "When Mara hesitates at the broken ascent, keep her competent and give the "
                        "player a natural chance to ask what she remembers or let her choose the route."
                    )
                },
                "is_active": True,
            },
        )
        PedagogicalIntervention.objects.update_or_create(
            adventure=template,
            objective=objective_map["repair-tension"],
            kind=PedagogicalIntervention.Kind.REPAIR,
            defaults={
                "payload": {
                    "constraint": (
                        "If the player was harsh, allow a concise in-world repair attempt that can "
                        "restore some cooperation without erasing the earlier cost."
                    )
                },
                "is_active": True,
            },
        )
        PedagogicalIntervention.objects.update_or_create(
            adventure=template,
            objective=objective_map["share-agency"],
            kind=PedagogicalIntervention.Kind.CHOICE_CARDS,
            defaults={
                "payload": {
                    "cards": {
                        "en": [
                            "Slow down and ask Mara what she remembers about the tower.",
                            "Let Mara choose the route while you secure the broken stair.",
                            "Ask what support would make the climb safer for both of you.",
                            "If the exchange became tense, acknowledge it and reset the plan.",
                        ],
                        "ru": [
                            "Не спешить и спросить Мару, что она помнит о башне.",
                            "Позволить Маре выбрать путь, пока вы укрепляете разрушенную лестницу.",
                            "Спросить, какая помощь сделает подъём безопаснее для вас обоих.",
                            "Если разговор стал напряжённым, признать это и пересобрать план.",
                        ],
                    }
                },
                "is_active": True,
            },
        )

        AdventureEvent.objects.update_or_create(
            adventure=template,
            title="Broken ascent in the sleet",
            defaults={
                "location": trail,
                "status": AdventureEvent.Status.ACTIVE,
                "trigger_hint": (
                    "The main ascent has collapsed. Mara stops at the broken stair and studies the "
                    "ice-covered masonry. She may know another way into the tower."
                ),
                "state": (
                    "Keep this as a tense adventure scene. Give the player room to ask for Mara's "
                    "knowledge, share the risk, pressure her, or choose another approach. A first "
                    "constructive choice may reveal traces of an old builders' route, but do not "
                    "open the hidden maintenance entrance immediately."
                ),
            },
        )
        AdventureEvent.objects.update_or_create(
            adventure=template,
            title="Hidden maintenance route",
            defaults={
                "location": tower,
                "status": AdventureEvent.Status.INACTIVE,
                "trigger_hint": (
                    "If trust and cooperation with Mara are strong enough, she remembers a narrow "
                    "maintenance passage below the eastern gallery."
                ),
                "state": (
                    "The route is a richer opportunity, not a reward screen. If it does not open, "
                    "the exposed climb remains possible but riskier and more costly."
                ),
            },
        )
        AdventureEvent.objects.update_or_create(
            adventure=template,
            title="Relight the beacon before dawn",
            defaults={
                "location": tower,
                "status": AdventureEvent.Status.ACTIVE,
                "trigger_hint": (
                    "At the tower summit, the player must repair and light the storm-damaged beacon "
                    "before raiders test the border road."
                ),
                "state": (
                    "This is the primary mission and a real deadline: reach the tower, repair the "
                    "storm-damaged beacon, and relight it before raider scouts secure the pass. "
                    "Advance toward the tower instead of repeating travel beats. Bring earlier "
                    "choices back through trust, access, risk, and cooperation. Avoid explicit "
                    "moral scores or didactic narration."
                ),
            },
        )
        AdventureEvent.objects.update_or_create(
            adventure=template,
            title="Raider scouts below the pass",
            defaults={
                "location": trail,
                "status": AdventureEvent.Status.ACTIVE,
                "trigger_hint": (
                    "After the first meaningful move, reveal torchlight, horn signals, tracks, or "
                    "a direct encounter: raider scouts are climbing toward the tower."
                ),
                "state": (
                    "Keep external pressure visible. Within the next scene, introduce a concrete "
                    "sign of the Raider Pathfinder or a direct obstacle caused by him: lantern "
                    "light, a horn signal, a shot, falling stones, or a close encounter. Let combat, "
                    "traversal, or beacon magic matter. Do not spend multiple turns only describing "
                    "sleet and climbing."
                ),
            },
        )
        PublishedAdventure.objects.get_or_create(adventure=template)

        action = "Created" if template_created else "Updated"
        self.stdout.write(self.style.SUCCESS(f"{action} demo template {template.id}: {template.title}"))
        self.stdout.write(self.style.SUCCESS("Published demo template."))
        if password:
            account_action = "Created" if user_created else "Updated"
            self.stdout.write(
                self.style.SUCCESS(
                    f"{account_action} demo login: username={username} password={password}"
                )
            )
