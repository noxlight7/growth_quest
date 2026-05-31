from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("adventures", "0013_character_in_party"),
    ]

    operations = [
        migrations.AddField(
            model_name="adventure",
            name="is_waiting_ai",
            field=models.BooleanField(default=False),
        ),
    ]
