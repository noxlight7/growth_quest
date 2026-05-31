from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("adventures", "0018_remove_technique_adventure"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="charactersystem",
            name="uq_character_system",
        ),
        migrations.RemoveIndex(
            model_name="charactersystem",
            name="idx_character_systems_adv",
        ),
        migrations.RemoveField(
            model_name="charactersystem",
            name="adventure",
        ),
        migrations.AddConstraint(
            model_name="charactersystem",
            constraint=models.UniqueConstraint(
                fields=("character", "system"),
                name="uq_character_system",
            ),
        ),
        migrations.AddIndex(
            model_name="charactersystem",
            index=models.Index(fields=["character"], name="idx_char_systems_char"),
        ),
        migrations.RemoveConstraint(
            model_name="charactertechnique",
            name="uq_character_technique",
        ),
        migrations.RemoveIndex(
            model_name="charactertechnique",
            name="idx_character_techniques_adv",
        ),
        migrations.RemoveField(
            model_name="charactertechnique",
            name="adventure",
        ),
        migrations.AddConstraint(
            model_name="charactertechnique",
            constraint=models.UniqueConstraint(
                fields=("character", "technique"),
                name="uq_character_technique",
            ),
        ),
        migrations.AddIndex(
            model_name="charactertechnique",
            index=models.Index(fields=["character"], name="idx_char_techniques_char"),
        ),
    ]
