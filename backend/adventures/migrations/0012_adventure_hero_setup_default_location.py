from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("adventures", "0011_adventure_hero_setup_defaults"),
    ]

    operations = [
        migrations.AddField(
            model_name="adventureherosetup",
            name="default_location",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="default_for_hero_setup",
                to="adventures.location",
            ),
        ),
    ]
