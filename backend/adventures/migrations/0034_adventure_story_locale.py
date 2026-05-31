from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("adventures", "0033_character_story_status"),
    ]

    operations = [
        migrations.AddField(
            model_name="adventure",
            name="story_locale",
            field=models.CharField(
                choices=[("ru", "ru"), ("en", "en"), ("zh-CN", "zh-CN")],
                default="ru",
                max_length=8,
            ),
        ),
        migrations.AlterField(
            model_name="adventure",
            name="story_locale",
            field=models.CharField(
                choices=[("ru", "ru"), ("en", "en"), ("zh-CN", "zh-CN")],
                default="en",
                max_length=8,
            ),
        ),
    ]
