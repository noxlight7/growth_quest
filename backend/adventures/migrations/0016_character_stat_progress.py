from django.db import migrations, models
from django.db.models import Q


class Migration(migrations.Migration):
    dependencies = [
        ("adventures", "0015_adventure_rollback_min_history"),
    ]

    operations = [
        migrations.AddField(
            model_name="character",
            name="body_power_progress",
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name="character",
            name="mind_power_progress",
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name="character",
            name="will_power_progress",
            field=models.IntegerField(default=0),
        ),
        migrations.AddConstraint(
            model_name="character",
            constraint=models.CheckConstraint(
                name="characters_body_progress_range",
                condition=Q(body_power_progress__gte=0) & Q(body_power_progress__lte=100),
            ),
        ),
        migrations.AddConstraint(
            model_name="character",
            constraint=models.CheckConstraint(
                name="characters_mind_progress_range",
                condition=Q(mind_power_progress__gte=0) & Q(mind_power_progress__lte=100),
            ),
        ),
        migrations.AddConstraint(
            model_name="character",
            constraint=models.CheckConstraint(
                name="characters_will_progress_range",
                condition=Q(will_power_progress__gte=0) & Q(will_power_progress__lte=100),
            ),
        ),
    ]
