"""Create an educational demo adventure template for the contest MVP."""
from __future__ import annotations

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from adventures.models import (
    Adventure,
    AdventureEvent,
    AdventureHeroSetup,
    Character,
    LearningObjective,
    Location,
    PedagogicalIntervention,
    Race,
    ReflectionPrompt,
)


class Command(BaseCommand):
    help = "Seed the AI for Education demo scenario pack."

    def add_arguments(self, parser):
        parser.add_argument("--username", default="demo_teacher")
        parser.add_argument(
            "--password",
            default="demo12345",
            help="Password to set for the local demo teacher account.",
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
        template, created = Adventure.objects.get_or_create(
            author_user=user,
            is_template=True,
            player_user=None,
            template_adventure=None,
            title="Growth-Oriented Demo Scenario",
            defaults={
                "description": (
                    "A school/community story set in a contemporary Chinese city. "
                    "Players navigate group responsibility, care for a classmate, "
                    "family support, inclusion, and digital wellbeing."
                ),
                "intro": (
                    "<main_hero> joins a class team preparing a community lantern exhibition. "
                    "A popular student wants to hide a mistake, a new classmate needs an "
                    "accommodation, and a grandparent asks for help at the neighborhood center."
                ),
                "spec_instructions": (
                    "Keep scenes age-appropriate for 15+ players. Avoid graphic harm, sexual "
                    "content, extremism, and political topics. Present choices with consequences "
                    "and opportunities for repair, help-seeking, and inclusion. Keep growth goals "
                    "expressed through the world, NPC trust, and available repair paths."
                ),
                "story_locale": Adventure.StoryLocale.EN,
                "facilitator_enabled": True,
                "growth_analysis_enabled": True,
                "narrative_consequences_enabled": True,
            },
        )
        if not created:
            if template.story_locale != Adventure.StoryLocale.EN:
                template.story_locale = Adventure.StoryLocale.EN
                template.save(update_fields=["story_locale", "updated_at"])
            self.stdout.write(self.style.WARNING("Demo template already exists."))
            if password:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Demo login: username={username} password={password}"
                    )
                )
            return

        school = Location.objects.create(
            adventure=template,
            title="Riverside High School",
            description="Classrooms, a courtyard, and a student activity room preparing a community exhibition.",
            tags=["school", "community", "china"],
        )
        center = Location.objects.create(
            adventure=template,
            title="Neighborhood Service Center",
            description="A public center where students help families and older residents with the lantern event.",
            x=2,
            y=1,
            tags=["family", "community"],
        )
        Race.objects.create(
            adventure=template,
            title="Student",
            description="Players aged 15+ in a school/community pilot scenario.",
            tags=["player"],
        )
        hero = Character.objects.create(
            adventure=template,
            location=school,
            is_player=True,
            in_party=True,
            title="Team Coordinator",
            age=16,
            body_power=1,
            mind_power=2,
            will_power=2,
            description="A student asked to help the class team make fair and responsible choices.",
            tags=["player", "student"],
        )
        Character.objects.create(
            adventure=template,
            location=school,
            title="Lin Yue",
            age=16,
            description="A new classmate who uses text-to-speech notes and needs quiet time during group work.",
            tags=["inclusion", "classmate"],
        )
        Character.objects.create(
            adventure=template,
            location=center,
            title="Grandmother Chen",
            age=72,
            description="A neighborhood volunteer who asks students to balance family care with school duties.",
            tags=["family", "intergenerational"],
        )
        template.primary_heroes.set([hero])
        AdventureHeroSetup.objects.update_or_create(
            adventure=template,
            defaults={
                "default_location": school,
                "require_race": False,
                "require_age": False,
                "default_age": 16,
                "require_body_power": False,
                "default_body_power": 1,
                "require_mind_power": False,
                "default_mind_power": 2,
                "require_will_power": False,
                "default_will_power": 2,
            },
        )
        objectives = [
            ("empathy-perspective", "Empathy in conflict", "empathy", 5),
            ("team-responsibility", "Cooperation and shared responsibility", "cooperation", 5),
            ("pause-before-posting", "Self-regulation in digital conflict", "self_regulation", 4),
            ("repair-trust", "Restorative action after harm", "restorative_action", 4),
            ("ask-for-help", "Help-seeking and trusted adults", "help_seeking", 3),
            ("inclusive-workflow", "Inclusive accommodation", "inclusion", 4),
        ]
        objective_map = {}
        for code, title, competency, weight in objectives:
            objective_map[code] = LearningObjective.objects.create(
                adventure=template,
                code=code,
                title=title,
                description=f"Observe evidence markers for {competency.replace('_', ' ')}.",
                competency=competency,
                weight=weight,
            )
        ReflectionPrompt.objects.create(
            adventure=template,
            objective=objective_map["empathy-perspective"],
            question="Hero journal: what clue suggests Lin Yue's perspective should matter before the next choice?",
        )
        ReflectionPrompt.objects.create(
            adventure=template,
            objective=objective_map["repair-trust"],
            question="If the group made a harmful choice, what repair step could rebuild trust?",
        )
        ReflectionPrompt.objects.create(
            adventure=template,
            objective=objective_map["inclusive-workflow"],
            question="What small accommodation would let everyone contribute without making anyone feel singled out?",
        )
        PedagogicalIntervention.objects.create(
            adventure=template,
            objective=objective_map["team-responsibility"],
            kind=PedagogicalIntervention.Kind.CHOICE_CARDS,
            payload={
                "cards": {
                    "ru": [
                        "Попросить группу сделать паузу и выслушать Линь Юэ перед решением.",
                        "Предложить рассказать ответственному взрослому об ошибке и подготовить план исправления.",
                        "Попросить бабушку Чэнь объяснить, какая помощь нужна центру.",
                        "Перенести шумную задачу наружу, чтобы заметки с озвучиванием оставались удобными.",
                    ],
                    "en": [
                        "Ask the group to pause and hear Lin Yue's view before deciding.",
                        "Suggest telling a responsible adult about the mistake and offering a repair plan.",
                        "Invite Grandmother Chen to explain what support the community center needs.",
                        "Move the noisy task outside so text-to-speech notes remain usable.",
                    ],
                    "zh-CN": [
                        "请小组先暂停，在决定前听听林悦的想法。",
                        "建议把错误告诉负责任的成年人，并提出补救计划。",
                        "邀请陈奶奶说明社区中心需要哪些支持。",
                        "把吵闹的任务移到外面，让文字转语音笔记可以继续使用。",
                    ],
                }
            },
        )
        AdventureEvent.objects.create(
            adventure=template,
            location=school,
            title="Hidden mistake in the lantern design",
            trigger_hint="A teammate suggests hiding an error to protect the class reputation.",
            state="Use this as a responsible decision and restorative action dilemma.",
        )
        AdventureEvent.objects.create(
            adventure=template,
            location=school,
            title="Bullying in the group chat",
            trigger_hint="A meme about Lin Yue starts spreading before the exhibition.",
            state="Use a safe anti-bullying and help-seeking scene.",
        )
        AdventureEvent.objects.create(
            adventure=template,
            location=center,
            title="Family and community responsibility",
            trigger_hint="Students must balance rehearsal time with helping older residents.",
            state="Use intergenerational care and cooperation without prescribing one family model.",
        )
        self.stdout.write(self.style.SUCCESS(f"Created demo template {template.id}: {template.title}"))
        if password:
            prefix = "Created" if user_created else "Updated"
            self.stdout.write(
                self.style.SUCCESS(
                    f"{prefix} demo login: username={username} password={password}"
                )
            )
