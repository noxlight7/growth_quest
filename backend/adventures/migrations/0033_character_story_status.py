from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("adventures", "0032_turn_analysis_log_snapshot"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql=[
                        (
                            "ALTER TABLE adventures_character "
                            "ADD COLUMN IF NOT EXISTS story_status varchar(16) "
                            "NOT NULL DEFAULT 'active';",
                            None,
                        ),
                        (
                            "ALTER TABLE adventures_character "
                            "ALTER COLUMN story_status DROP DEFAULT;",
                            None,
                        ),
                    ],
                    reverse_sql=(
                        "ALTER TABLE adventures_character "
                        "DROP COLUMN IF EXISTS story_status;"
                    ),
                ),
            ],
            state_operations=[
                migrations.AddField(
                    model_name="character",
                    name="story_status",
                    field=models.CharField(
                        choices=[
                            ("active", "active"),
                            ("dead", "dead"),
                            ("missing", "missing"),
                            ("inactive", "inactive"),
                        ],
                        default="active",
                        max_length=16,
                    ),
                ),
            ],
        ),
    ]
