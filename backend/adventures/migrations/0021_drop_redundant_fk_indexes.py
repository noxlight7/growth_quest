from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("adventures", "0020_update_adventure_consistency_triggers"),
    ]

    operations = [
        migrations.RemoveIndex(
            model_name="technique",
            name="idx_techniques_system",
        ),
        migrations.RemoveIndex(
            model_name="charactersystem",
            name="idx_char_systems_char",
        ),
        migrations.RemoveIndex(
            model_name="charactertechnique",
            name="idx_char_techniques_char",
        ),
    ]
