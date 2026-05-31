from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("adventures", "0031_narrative_consequence_certainty_and_analysis_log"),
    ]

    operations = [
        migrations.AddField(
            model_name="turnanalysislog",
            name="snapshot",
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
