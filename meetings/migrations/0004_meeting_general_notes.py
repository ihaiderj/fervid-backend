import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("meetings", "0003_meeting_location_nullable"),
    ]

    operations = [
        migrations.CreateModel(
            name="MeetingNote",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("title", models.TextField(blank=True, default="")),
                ("notes", models.TextField(blank=True, default="")),
                ("is_deleted", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "meeting",
                    models.ForeignKey(
                        db_column="meeting_id",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="general_notes",
                        to="meetings.meeting",
                    ),
                ),
            ],
            options={
                "db_table": "meeting_notes",
                "ordering": ["-created_at"],
            },
        ),
    ]
