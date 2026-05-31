from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
from django.db.models import Q


class Migration(migrations.Migration):
    dependencies = [
        ("adventures", "0023_update_faction_relationship_triggers"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="adventure",
            name="max_players",
            field=models.PositiveSmallIntegerField(default=5),
        ),
        migrations.AddField(
            model_name="adventure",
            name="invite_token",
            field=models.CharField(blank=True, max_length=64, null=True, unique=True),
        ),
        migrations.AddField(
            model_name="adventure",
            name="shared_location",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="shared_in_adventures",
                to="adventures.location",
            ),
        ),
        migrations.AddField(
            model_name="adventure",
            name="started_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.CreateModel(
            name="AdventurePlayer",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("slot_number", models.PositiveSmallIntegerField()),
                ("wrote_after_ai", models.BooleanField(default=False)),
                ("joined_at", models.DateTimeField(auto_now_add=True)),
                (
                    "adventure",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="players",
                        to="adventures.adventure",
                    ),
                ),
                (
                    "hero",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="player_slots",
                        to="adventures.character",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="adventure_memberships",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "constraints": [
                    models.UniqueConstraint(
                        fields=["adventure", "user"],
                        name="uq_adventure_player_user",
                    ),
                    models.UniqueConstraint(
                        fields=["adventure", "slot_number"],
                        name="uq_adventure_player_slot",
                    ),
                    models.UniqueConstraint(
                        condition=Q(("hero__isnull", False)),
                        fields=["adventure", "hero"],
                        name="uq_adventure_player_hero",
                    ),
                ],
            },
        ),
    ]
