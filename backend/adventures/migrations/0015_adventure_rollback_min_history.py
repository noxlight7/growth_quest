from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("adventures", "0014_adventure_is_waiting_ai"),
    ]

    operations = [
        migrations.AddField(
            model_name="adventure",
            name="rollback_min_history_id",
            field=models.BigIntegerField(blank=True, null=True),
        ),
    ]
