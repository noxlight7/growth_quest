from django.db import migrations, models
import django.db.models.deletion
from django.db.models import Q


class Migration(migrations.Migration):
    dependencies = [
        ("adventures", "0010_adventure_hero_setup"),
    ]

    operations = [
        migrations.AddField(
            model_name="adventureherosetup",
            name="default_race",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="default_for_hero_setup",
                to="adventures.race",
            ),
        ),
        migrations.AddField(
            model_name="adventureherosetup",
            name="default_age",
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="adventureherosetup",
            name="default_body_power",
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="adventureherosetup",
            name="default_mind_power",
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="adventureherosetup",
            name="default_will_power",
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddConstraint(
            model_name="adventureherosetup",
            constraint=models.CheckConstraint(
                name="hero_setup_default_age_nonneg",
                condition=Q(default_age__gte=0) | Q(default_age__isnull=True),
            ),
        ),
        migrations.AddConstraint(
            model_name="adventureherosetup",
            constraint=models.CheckConstraint(
                name="hero_setup_default_body_nonneg",
                condition=Q(default_body_power__gte=0) | Q(default_body_power__isnull=True),
            ),
        ),
        migrations.AddConstraint(
            model_name="adventureherosetup",
            constraint=models.CheckConstraint(
                name="hero_setup_default_mind_nonneg",
                condition=Q(default_mind_power__gte=0) | Q(default_mind_power__isnull=True),
            ),
        ),
        migrations.AddConstraint(
            model_name="adventureherosetup",
            constraint=models.CheckConstraint(
                name="hero_setup_default_will_nonneg",
                condition=Q(default_will_power__gte=0) | Q(default_will_power__isnull=True),
            ),
        ),
    ]
