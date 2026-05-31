from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("adventures", "0012_adventure_hero_setup_default_location"),
    ]

    operations = [
        migrations.AddField(
            model_name="character",
            name="in_party",
            field=models.BooleanField(default=False),
        ),
        migrations.AddIndex(
            model_name="character",
            index=models.Index(fields=["adventure", "in_party"], name="idx_characters_in_party"),
        ),
    ]
