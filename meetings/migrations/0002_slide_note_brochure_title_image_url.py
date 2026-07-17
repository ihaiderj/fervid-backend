from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("meetings", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="meetingslidenote",
            name="brochure_title",
            field=models.TextField(blank=True, default=""),
        ),
    ]
