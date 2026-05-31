import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("adventures", "0030_adventure_growth_analysis_enabled_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="narrativeconsequence",
            name="certainty",
            field=models.CharField(
                choices=[
                    ("intent", "intent"),
                    ("attempted", "attempted"),
                    ("established", "established"),
                ],
                default="established",
                max_length=16,
            ),
        ),
        migrations.RemoveIndex(
            model_name="narrativeconsequence",
            name="idx_narrative_conseq_active",
        ),
        migrations.AddIndex(
            model_name="narrativeconsequence",
            index=models.Index(
                fields=["adventure", "status", "certainty", "-importance", "-updated_at"],
                name="idx_narrative_conseq_scope",
            ),
        ),
        migrations.CreateModel(
            name="TurnAnalysisLog",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "kind",
                    models.CharField(
                        choices=[
                            ("player_turn", "player_turn"),
                            ("world_confirmation", "world_confirmation"),
                        ],
                        max_length=32,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("ok", "ok"),
                            ("invalid_output", "invalid_output"),
                            ("error", "error"),
                        ],
                        max_length=32,
                    ),
                ),
                ("raw_response", models.TextField(blank=True)),
                ("error", models.TextField(blank=True)),
                ("result_counts", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "adventure",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="turn_analysis_logs",
                        to="adventures.adventure",
                    ),
                ),
                (
                    "history_entry",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="turn_analysis_logs",
                        to="adventures.adventurehistory",
                    ),
                ),
            ],
        ),
        migrations.AddIndex(
            model_name="turnanalysislog",
            index=models.Index(
                fields=["adventure", "-created_at"],
                name="idx_turn_analysis_adv",
            ),
        ),
        migrations.AddIndex(
            model_name="turnanalysislog",
            index=models.Index(
                fields=["status", "-created_at"],
                name="idx_turn_analysis_status",
            ),
        ),
    ]
