from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("brochures", "0002_normalize_saved_brochure_ids"),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name="savedbrochure",
            unique_together=set(),
        ),
        migrations.AddIndex(
            model_name="savedbrochure",
            index=models.Index(fields=["mr", "brochure_id"], name="saved_broch_mr_broch_idx"),
        ),
    ]
