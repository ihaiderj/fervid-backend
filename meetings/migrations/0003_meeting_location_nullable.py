from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("meetings", "0002_slide_note_brochure_title_image_url"),
    ]

    operations = [
        migrations.AlterField(
            model_name="meeting",
            name="location",
            field=models.TextField(blank=True, null=True),
        ),
    ]
