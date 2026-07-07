"""Create the school/community scenario for the live competition presentation."""
from __future__ import annotations

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from adventures.models import (
    Adventure,
    AdventureEvent,
    AdventureHeroSetup,
    Character,
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
    help = "Seed the Riverside Futures Fair school/community demo scenario."

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
            title="Riverside Futures Fair",
            defaults={
                "description": (
                    "A present-day story about students preparing a public booth for a neighborhood "
                    "futures fair. A deadline, a flawed map, and competing requests force the team "
                    "to decide who to listen to and what to fix before visitors arrive."
                ),
                "intro": (
                    "<main_hero> coordinates a student team preparing a booth for the Riverside "
                    "Futures Fair. Visitors arrive this afternoon. The team has a route map, a "
                    "tabletop demo, and a stack of unfinished signs, but one route card is still "
                    "unverified and the service center is waiting for a final check. The next "
                    "hour will decide whether the booth feels rushed or genuinely useful."
                ),
                "spec_instructions": (
                    "Keep this as a grounded present-day story, not a lecture, quiz, therapy "
                    "session, or political debate. The target pilot age is 15+. Avoid graphic harm, "
                    "sexual content, extremism, partisan politics, stereotypes, and hidden diagnosis "
                    "of the player. Do not reveal every problem immediately. Let the story surface "
                    "practical tensions through missing details, people who were not heard, time "
                    "pressure, and visible consequences at the fair. The player should face several "
                    "respectable paths, not one obvious moral button. If the player makes a careless "
                    "or harmful choice, keep the story playable and open a believable way to repair "
                    "trust or correct the public materials. Do not narrate unspoken thoughts, "
                    "feelings, or motives for the player character."
                ),
                "story_locale": Adventure.StoryLocale.EN,
                "facilitator_enabled": True,
                "growth_analysis_enabled": True,
                "narrative_consequences_enabled": True,
                "max_players": 4,
            },
        )

        school, _ = Location.objects.update_or_create(
            adventure=template,
            title="Riverside High School",
            defaults={
                "description": (
                    "Classrooms, a courtyard, and a busy student activity room where the futures "
                    "fair team is assembling route cards, signs, and a tabletop demo."
                ),
                "x": 0,
                "y": 0,
                "tags": ["school", "community", "presentation"],
            },
        )
        center, _ = Location.objects.update_or_create(
            adventure=template,
            title="Neighborhood Service Center",
            defaults={
                "description": (
                    "A nearby public center where older residents and volunteers are preparing "
                    "their own table for the fair and waiting for student support."
                ),
                "x": 1,
                "y": 0,
                "tags": ["community", "intergenerational", "support"],
            },
        )
        hall, _ = Location.objects.update_or_create(
            adventure=template,
            title="Exhibition Hall",
            defaults={
                "description": (
                    "The final public space for the futures fair. Visitors will see whether the "
                    "booth is rushed, confusing, or useful enough to trust."
                ),
                "x": 1,
                "y": 1,
                "tags": ["fair", "public", "consequence"],
            },
        )

        student_race, _ = Race.objects.update_or_create(
            adventure=template,
            title="Student",
            defaults={
                "description": "A 15+ student in a school/community pilot scenario.",
                "tags": ["player", "student"],
            },
        )
        adult_race, _ = Race.objects.update_or_create(
            adventure=template,
            title="Community Adult",
            defaults={
                "description": "An adult mentor, volunteer, or resident in the community story.",
                "tags": ["adult", "community"],
            },
        )

        hero, _ = Character.objects.update_or_create(
            adventure=template,
            title="Student Coordinator",
            defaults={
                "race": student_race,
                "location": school,
                "is_player": True,
                "in_party": True,
                "age": 16,
                "body_power": 1,
                "mind_power": 2,
                "will_power": 2,
                "description": (
                    "The student coordinating the final afternoon before the Riverside Futures "
                    "Fair. The coordinator must balance speed, fairness, honesty, and care for "
                    "the wider community."
                ),
                "tags": ["player", "student", "coordinator"],
            },
        )
        lin_yue, _ = Character.objects.update_or_create(
            adventure=template,
            title="Lin Yue",
            defaults={
                "race": student_race,
                "location": school,
                "is_player": False,
                "in_party": True,
                "age": 16,
                "body_power": 1,
                "mind_power": 2,
                "will_power": 2,
                "description": (
                    "A new classmate who keeps careful notes and often catches details others miss. "
                    "Lin Yue works best when the room is quieter, but does not want the team to make "
                    "a spectacle of that."
                ),
                "tags": ["npc", "classmate", "inclusion", "digital-wellbeing"],
            },
        )
        hao, _ = Character.objects.update_or_create(
            adventure=template,
            title="Hao Ming",
            defaults={
                "race": student_race,
                "location": school,
                "is_player": False,
                "in_party": True,
                "age": 16,
                "body_power": 1,
                "mind_power": 2,
                "will_power": 1,
                "description": (
                    "A capable visual designer under pressure. Hao Ming wants the fair to look "
                    "impressive and is tempted to hide a mistake that could embarrass the team."
                ),
                "tags": ["npc", "classmate", "reputation", "pressure"],
            },
        )
        grandmother_chen, _ = Character.objects.update_or_create(
            adventure=template,
            title="Grandmother Chen",
            defaults={
                "race": adult_race,
                "location": center,
                "is_player": False,
                "in_party": False,
                "age": 72,
                "body_power": 1,
                "mind_power": 2,
                "will_power": 2,
                "description": (
                    "A neighborhood volunteer preparing a community table about family learning "
                    "and digital access for older residents. She asks students for practical help, "
                    "not pity."
                ),
                "tags": ["npc", "community", "intergenerational", "volunteer"],
            },
        )
        ms_rao, _ = Character.objects.update_or_create(
            adventure=template,
            title="Ms. Rao",
            defaults={
                "race": adult_race,
                "location": school,
                "is_player": False,
                "in_party": False,
                "age": 35,
                "body_power": 1,
                "mind_power": 3,
                "will_power": 2,
                "description": (
                    "The adult facilitator for the fair. She can help students check risks and "
                    "available options, but she should not solve every choice for them."
                ),
                "tags": ["npc", "facilitator", "mentor"],
            },
        )

        template.primary_heroes.set([hero])
        template.primary_hero = hero
        template.shared_location = school
        template.max_players = 4
        template.save(update_fields=["primary_hero", "shared_location", "max_players", "updated_at"])

        AdventureHeroSetup.objects.update_or_create(
            adventure=template,
            defaults={
                "default_location": school,
                "require_race": False,
                "default_race": student_race,
                "require_age": False,
                "default_age": 16,
                "require_body_power": False,
                "default_body_power": 1,
                "require_mind_power": False,
                "default_mind_power": 2,
                "require_will_power": False,
                "default_will_power": 2,
                "require_systems": False,
                "require_techniques": False,
            },
        )

        systems = [
            (
                "Project Coordination",
                {
                    "description": (
                        "Planning under deadline pressure, dividing work fairly, and keeping the "
                        "team focused without taking over everyone's role."
                    ),
                    "tags": ["teamwork", "planning", "leadership"],
                    "w_body": 0,
                    "w_mind": 2,
                    "w_will": 2,
                    "formula_hint": "Rewards fair planning, calm prioritization, and shared agency.",
                },
            ),
            (
                "Digital Mediation",
                {
                    "description": (
                        "Handling group chat conflict, slowing down impulsive posting, and moving "
                        "toward accountable repair."
                    ),
                    "tags": ["digital-wellbeing", "self-regulation", "repair"],
                    "w_body": 0,
                    "w_mind": 2,
                    "w_will": 3,
                    "formula_hint": "Rewards pausing, checking facts, and asking for trusted help.",
                },
            ),
            (
                "Community Interviewing",
                {
                    "description": (
                        "Listening to residents, translating needs into practical tasks, and "
                        "presenting community voices respectfully."
                    ),
                    "tags": ["community", "empathy", "intergenerational"],
                    "w_body": 0,
                    "w_mind": 3,
                    "w_will": 1,
                    "formula_hint": "Rewards careful listening and concrete support.",
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
                "Project Coordination",
                "Role Rotation",
                {
                    "description": (
                        "Redistribute tasks so quieter team members can contribute visibly without "
                        "being put on display."
                    ),
                    "tags": ["teamwork", "inclusion"],
                    "difficulty": 2,
                    "tier": 1,
                    "required_system_level": 1,
                },
            ),
            (
                "Project Coordination",
                "Repair Plan",
                {
                    "description": (
                        "Turn an error into a concrete disclosure, fix, and follow-up commitment "
                        "before it damages trust."
                    ),
                    "tags": ["responsibility", "repair"],
                    "difficulty": 3,
                    "tier": 1,
                    "required_system_level": 2,
                },
            ),
            (
                "Digital Mediation",
                "Pause the Chat",
                {
                    "description": (
                        "Slow down a harmful group chat thread, check context, and move the issue "
                        "to a safer channel."
                    ),
                    "tags": ["self-regulation", "digital-conflict"],
                    "difficulty": 2,
                    "tier": 1,
                    "required_system_level": 1,
                },
            ),
            (
                "Digital Mediation",
                "Trusted Adult Check",
                {
                    "description": (
                        "Ask a facilitator for help with a conflict while keeping student agency "
                        "and privacy intact."
                    ),
                    "tags": ["help-seeking", "safety"],
                    "difficulty": 2,
                    "tier": 1,
                    "required_system_level": 1,
                },
            ),
            (
                "Community Interviewing",
                "Needs Map",
                {
                    "description": (
                        "Translate resident requests into visible tasks, priorities, and fair "
                        "commitments."
                    ),
                    "tags": ["community", "planning"],
                    "difficulty": 2,
                    "tier": 1,
                    "required_system_level": 1,
                },
            ),
            (
                "Community Interviewing",
                "Respectful Listening",
                {
                    "description": (
                        "Invite a community member's perspective without making them a symbol or "
                        "treating help as charity."
                    ),
                    "tags": ["empathy", "intergenerational"],
                    "difficulty": 2,
                    "tier": 1,
                    "required_system_level": 1,
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
            (hero, "Project Coordination", 2, "Responsible for keeping the fair team aligned."),
            (hero, "Digital Mediation", 2, "Can slow down conflict without escalating it."),
            (lin_yue, "Community Interviewing", 2, "Has strong research notes on digital wellbeing."),
            (hao, "Project Coordination", 1, "Strong at presentation design, weaker under pressure."),
            (grandmother_chen, "Community Interviewing", 3, "Understands resident needs at the center."),
        ]
        for character, system_title, level, notes in character_systems:
            CharacterSystem.objects.update_or_create(
                character=character,
                system=system_map[system_title],
                defaults={"level": level, "progress_percent": 0, "notes": notes},
            )

        character_techniques = [
            (hero, "Role Rotation"),
            (hero, "Repair Plan"),
            (hero, "Pause the Chat"),
            (hero, "Trusted Adult Check"),
            (lin_yue, "Needs Map"),
            (lin_yue, "Respectful Listening"),
            (grandmother_chen, "Needs Map"),
            (grandmother_chen, "Respectful Listening"),
        ]
        for character, technique_title in character_techniques:
            CharacterTechnique.objects.update_or_create(
                character=character,
                technique=technique_map[technique_title],
                defaults={"notes": "Available at the start of Riverside Futures Fair."},
            )

        other_info = [
            (
                "competition-fit",
                "AI for Education framing",
                (
                    "The scenario demonstrates personal development through team responsibility, "
                    "inclusive workflow, digital wellbeing, restorative action, and community care."
                ),
                ["ai-for-education", "wellbeing", "inclusion"],
            ),
            (
                "module-demo",
                "Psychological module demonstration",
                (
                    "The supportive module should create natural chances to ask for help, share "
                    "agency, slow down conflict, and repair trust without diagnosing the player."
                ),
                ["psychological-support", "observable-actions"],
            ),
            (
                "module-demo",
                "Moral cause-and-effect demonstration",
                (
                    "Earlier choices should return through trust, available help, public credibility, "
                    "and the quality of the final exhibition rather than a visible morality score."
                ),
                ["moral-consequence", "trust", "access"],
            ),
        ]
        for category, title, description, tags in other_info:
            OtherInfo.objects.update_or_create(
                adventure=template,
                category=category,
                title=title,
                defaults={"description": description, "tags": tags},
            )

        objectives = [
            (
                "inclusive-workflow",
                "Inclusive workflow without singling anyone out",
                LearningObjective.Competency.INCLUSION,
                5,
                (
                    "Notice choices that let Lin Yue contribute meaningfully while preserving "
                    "dignity and autonomy."
                ),
            ),
            (
                "responsible-repair",
                "Honest repair after a project mistake",
                LearningObjective.Competency.RESTORATIVE_ACTION,
                5,
                (
                    "Notice whether the player hides, shifts blame, or turns an error into a "
                    "credible repair plan."
                ),
            ),
            (
                "pause-before-posting",
                "Self-regulation in digital conflict",
                LearningObjective.Competency.SELF_REGULATION,
                4,
                (
                    "Notice whether the player slows down group chat conflict and seeks context "
                    "before reacting."
                ),
            ),
            (
                "shared-leadership",
                "Cooperation and shared agency under deadline pressure",
                LearningObjective.Competency.COOPERATION,
                4,
                (
                    "Notice choices that distribute responsibility instead of controlling or "
                    "abandoning the team."
                ),
            ),
            (
                "community-perspective",
                "Respectful community perspective-taking",
                LearningObjective.Competency.EMPATHY,
                4,
                (
                    "Notice whether the player treats residents as partners with knowledge, not "
                    "as props for a presentation."
                ),
            ),
            (
                "trusted-help",
                "Appropriate help-seeking",
                LearningObjective.Competency.HELP_SEEKING,
                3,
                (
                    "Notice whether the player asks Ms. Rao or community volunteers for help when "
                    "the issue exceeds what the team can safely handle alone."
                ),
            ),
        ]
        objective_map = {}
        for code, title, competency, weight, description in objectives:
            objective_map[code], _ = LearningObjective.objects.update_or_create(
                adventure=template,
                code=code,
                defaults={
                    "title": title,
                    "description": description,
                    "competency": competency,
                    "weight": weight,
                    "is_active": True,
                },
            )

        prompts = [
            (
                "inclusive-workflow",
                ReflectionPrompt.TriggerKind.KEY_CHOICE,
                (
                    "Hero journal: what would let Lin Yue's notes matter without turning her into "
                    "the center of attention?"
                ),
            ),
            (
                "responsible-repair",
                ReflectionPrompt.TriggerKind.KEY_CHOICE,
                "If the team admits the mistake, what concrete repair step should come with it?",
            ),
            (
                "pause-before-posting",
                ReflectionPrompt.TriggerKind.USER_TURN,
                "Before answering the group chat, what fact or perspective is still missing?",
            ),
            (
                "community-perspective",
                ReflectionPrompt.TriggerKind.KEY_CHOICE,
                (
                    "What does Grandmother Chen know about the fair that the student team might "
                    "miss if they only think about their own presentation?"
                ),
            ),
        ]
        for code, trigger_kind, question in prompts:
            ReflectionPrompt.objects.update_or_create(
                adventure=template,
                objective=objective_map[code],
                trigger_kind=trigger_kind,
                question=question,
                defaults={"is_active": True},
            )

        interventions = [
            (
                "inclusive-workflow",
                PedagogicalIntervention.Kind.PERSPECTIVE,
                {
                    "constraint": (
                        "When the team reorganizes tasks, give the player a natural chance to ask "
                        "Lin Yue what setup would help, without making Lin Yue passive or fragile."
                    )
                },
            ),
            (
                "responsible-repair",
                PedagogicalIntervention.Kind.DILEMMA,
                {
                    "constraint": (
                        "A visible design error appears close to the deadline. Present at least "
                        "two playable options: hide it and preserve speed, or disclose it with a "
                        "repair plan that costs time but builds credibility."
                    )
                },
            ),
            (
                "pause-before-posting",
                PedagogicalIntervention.Kind.REPAIR,
                {
                    "constraint": (
                        "If the group chat becomes harmful, open a repair path: pause the thread, "
                        "check context, ask a trusted adult if needed, and invite a concrete apology "
                        "or correction without public humiliation."
                    )
                },
            ),
            (
                "shared-leadership",
                PedagogicalIntervention.Kind.CHOICE_CARDS,
                {
                    "cards": {
                        "en": [
                            "Ask Lin Yue what she noticed in the route card before final printing.",
                            "Tell Hao Ming the map needs one more check, then split the fix.",
                            "Pause the chat and ask for the missing context before anyone posts again.",
                            "Ask Grandmother Chen which route residents actually use.",
                            "Ask Ms. Rao for a quick reality check, not a full rescue.",
                        ]
                    }
                },
            ),
        ]
        for code, kind, payload in interventions:
            PedagogicalIntervention.objects.update_or_create(
                adventure=template,
                objective=objective_map[code],
                kind=kind,
                defaults={"payload": payload, "is_active": True},
            )

        events = [
            (
                "The fair opens this afternoon",
                school,
                AdventureEvent.Status.ACTIVE,
                (
                    "The fair opens soon. The team must decide what to verify, who to ask, and "
                    "how much risk to accept before visitors arrive."
                ),
                (
                    "The team is preparing a public booth for the Riverside Futures Fair. Keep "
                    "the scene playable and concrete. The central pressure is a deadline, a public "
                    "presentation, and a team map/demo that may contain a practical error. Do not "
                    "reveal every problem immediately. After the first planning choice, surface one "
                    "concrete tension: someone noticed a mismatch in the booth materials, a quieter "
                    "teammate has useful information, or a community volunteer knows a local detail "
                    "the students missed. Track concrete earlier actions and let them affect later "
                    "help, accuracy, timing, and the final quality of the booth. "
                    "Do not use moral scores, labels, diagnoses, or explicit lesson language."
                ),
            ),
            (
                "Mismatched route card",
                school,
                AdventureEvent.Status.INACTIVE,
                (
                    "A route card or demo label may send visitors to the wrong room, time, or "
                    "service desk unless the team checks it before printing."
                ),
                (
                    "Use this as the core practical error. Hiding it preserves speed but risks "
                    "public trust. Correcting it costs time but can make the booth credible."
                ),
            ),
            (
                "Unheard note",
                school,
                AdventureEvent.Status.INACTIVE,
                (
                    "Lin Yue may have noticed the mismatch earlier, but the rushed room made it "
                    "easy for the team to miss or talk over the detail."
                ),
                (
                    "Let the player ask what Lin Yue noticed, create space for a practical "
                    "contribution, or ignore the clue. Consequences should affect trust and the "
                    "quality of the final booth."
                ),
            ),
            (
                "Message in the team chat",
                school,
                AdventureEvent.Status.INACTIVE,
                (
                    "A sharp message about the booth mistake or the rushed work may start spreading "
                    "in the student group chat."
                ),
                (
                    "Activate after a rushed or reputation-driven choice, or use as pressure near "
                    "the midpoint. Keep it safe: no slurs, graphic threats, or pile-on cruelty. "
                    "Focus on slowing down, checking context, and repairing the public record."
                ),
            ),
            (
                "Request from the service center",
                center,
                AdventureEvent.Status.INACTIVE,
                (
                    "Grandmother Chen may ask whether students can still check the route and signs "
                    "from the perspective of visitors coming from the service center."
                ),
                (
                    "Make this a tradeoff, not a side quest. Asking for local knowledge may cost "
                    "time but can reveal how visitors will actually use the booth."
                ),
            ),
            (
                "Visitors arrive",
                hall,
                AdventureEvent.Status.INACTIVE,
                (
                    "Visitors, families, classmates, and community volunteers arrive for the "
                    "Riverside Futures Fair."
                ),
                (
                    "Bring earlier choices back through visible trust, credibility, working "
                    "materials, and available support. Do not display a morality score."
                ),
            ),
        ]
        desired_event_titles = {title for title, *_ in events}
        AdventureEvent.objects.filter(adventure=template).exclude(
            title__in=desired_event_titles
        ).delete()
        for title, location, status, trigger_hint, state in events:
            AdventureEvent.objects.update_or_create(
                adventure=template,
                title=title,
                defaults={
                    "location": location,
                    "status": status,
                    "trigger_hint": trigger_hint,
                    "state": state,
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
