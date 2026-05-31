from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
from django.db.models import Q


def add_primary_heroes(apps, schema_editor):
    Adventure = apps.get_model("adventures", "Adventure")
    through = Adventure.primary_heroes.through
    for adventure in Adventure.objects.exclude(primary_hero_id=None).iterator():
        through.objects.get_or_create(
            adventure_id=adventure.id,
            character_id=adventure.primary_hero_id,
        )


def remove_primary_heroes(apps, schema_editor):
    Adventure = apps.get_model("adventures", "Adventure")
    through = Adventure.primary_heroes.through
    through.objects.filter(adventure_id__in=Adventure.objects.values_list("id", flat=True)).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("adventures", "0024_multi_player_lobby"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="adventure",
            name="primary_heroes",
            field=models.ManyToManyField(
                blank=True,
                related_name="primary_in_multi_adventures",
                to="adventures.character",
            ),
        ),
        migrations.AlterField(
            model_name="adventureplayer",
            name="user",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="adventure_memberships",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="adventureplayer",
            name="is_npc",
            field=models.BooleanField(default=False),
        ),
        migrations.AddConstraint(
            model_name="adventureplayer",
            constraint=models.CheckConstraint(
                condition=(Q(is_npc=False) & Q(user__isnull=False))
                | (Q(is_npc=True) & Q(user__isnull=True)),
                name="adventure_player_user_or_npc_chk",
            ),
        ),
        migrations.RunPython(add_primary_heroes, remove_primary_heroes),
    ]
