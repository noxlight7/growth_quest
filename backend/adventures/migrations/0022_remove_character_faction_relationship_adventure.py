from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("adventures", "0021_drop_redundant_fk_indexes"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="characterfaction",
            name="uq_characters_factions",
        ),
        migrations.RemoveIndex(
            model_name="characterfaction",
            name="idx_characters_factions_adv",
        ),
        migrations.RemoveField(
            model_name="characterfaction",
            name="adventure",
        ),
        migrations.AddConstraint(
            model_name="characterfaction",
            constraint=models.UniqueConstraint(
                fields=("character", "faction"),
                name="uq_characters_factions",
            ),
        ),
        migrations.AddIndex(
            model_name="characterfaction",
            index=models.Index(fields=["character"], name="idx_char_factions_char"),
        ),
        migrations.RemoveConstraint(
            model_name="characterrelationship",
            name="uq_relationship",
        ),
        migrations.RemoveIndex(
            model_name="characterrelationship",
            name="idx_rel_from",
        ),
        migrations.RemoveIndex(
            model_name="characterrelationship",
            name="idx_rel_to",
        ),
        migrations.RemoveIndex(
            model_name="characterrelationship",
            name="idx_rel_kind",
        ),
        migrations.RemoveField(
            model_name="characterrelationship",
            name="adventure",
        ),
        migrations.AddConstraint(
            model_name="characterrelationship",
            constraint=models.UniqueConstraint(
                fields=("from_character", "to_character", "kind"),
                name="uq_relationship",
            ),
        ),
        migrations.AddIndex(
            model_name="characterrelationship",
            index=models.Index(fields=["from_character"], name="idx_rel_from_char"),
        ),
        migrations.AddIndex(
            model_name="characterrelationship",
            index=models.Index(fields=["to_character"], name="idx_rel_to_char"),
        ),
        migrations.AddIndex(
            model_name="characterrelationship",
            index=models.Index(fields=["kind"], name="idx_rel_kind"),
        ),
    ]
