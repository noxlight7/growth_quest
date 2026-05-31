from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("adventures", "0017_moderation_publication"),
    ]

    operations = [
        migrations.RemoveIndex(
            model_name="technique",
            name="idx_techniques_adv_system",
        ),
        migrations.RemoveField(
            model_name="technique",
            name="adventure",
        ),
        migrations.AddIndex(
            model_name="technique",
            index=models.Index(fields=["system"], name="idx_techniques_system"),
        ),
    ]
