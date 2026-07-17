import uuid

from django.conf import settings
from django.db import models

from brochures.models import Brochure
from doctors.models import Doctor


class Meeting(models.Model):
    class Status(models.TextChoices):
        SCHEDULED = "scheduled", "Scheduled"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"
        RESCHEDULED = "rescheduled", "Rescheduled"
        ACTIVE = "active", "Active"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    mr = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="meetings",
        db_column="mr_id",
    )
    doctor = models.ForeignKey(
        Doctor, on_delete=models.CASCADE, related_name="meetings", db_column="doctor_id"
    )
    brochure = models.ForeignKey(
        Brochure,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="meetings",
        db_column="brochure_id",
    )
    title = models.CharField(max_length=255)
    scheduled_date = models.DateTimeField()
    duration_minutes = models.IntegerField(default=30)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.SCHEDULED
    )
    location = models.TextField(blank=True, null=True)
    notes = models.TextField(blank=True, default="")
    purpose = models.TextField(blank=True, default="")
    follow_up_required = models.BooleanField(default=False)
    follow_up_date = models.DateTimeField(null=True, blank=True)
    follow_up_time = models.TextField(blank=True, default="")
    follow_up_notes = models.TextField(blank=True, default="")
    presentation_slides = models.JSONField(default=dict, blank=True)
    comments = models.JSONField(default=dict, blank=True)
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "meetings"
        ordering = ["-scheduled_date"]

    def __str__(self):
        return self.title

    @property
    def brochure_title(self):
        if self.brochure:
            return self.brochure.title
        slides = self.presentation_slides or {}
        return slides.get("brochure_title", "")


class MeetingNote(models.Model):
    """General meeting note (title + notes). Distinct from slide notes; no brochure."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    meeting = models.ForeignKey(
        Meeting,
        on_delete=models.CASCADE,
        related_name="general_notes",
        db_column="meeting_id",
    )
    title = models.TextField(blank=True, default="")
    notes = models.TextField(blank=True, default="")
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "meeting_notes"
        ordering = ["-created_at"]

    def __str__(self):
        return self.title or f"Note ({self.meeting_id})"


class MeetingSlideNote(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    meeting = models.ForeignKey(
        Meeting,
        on_delete=models.CASCADE,
        related_name="slide_notes",
        db_column="meeting_id",
    )
    slide_id = models.TextField()
    slide_title = models.TextField(blank=True, default="")
    slide_order = models.IntegerField(default=0)
    brochure_id = models.TextField(blank=True, default="")
    brochure_title = models.TextField(blank=True, default="")
    note_text = models.TextField(blank=True, default="")
    slide_image_uri = models.TextField(blank=True, default="")
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "meeting_slide_notes"
        ordering = ["slide_order", "created_at"]

    def __str__(self):
        return f"Note on {self.slide_id} ({self.meeting_id})"


class MeetingFollowUp(models.Model):
    class Status(models.TextChoices):
        SCHEDULED = "scheduled", "Scheduled"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    meeting = models.ForeignKey(
        Meeting,
        on_delete=models.CASCADE,
        related_name="followups",
        db_column="meeting_id",
    )
    follow_up_date = models.DateTimeField()
    follow_up_time = models.TextField(blank=True, default="")
    follow_up_notes = models.TextField(blank=True, default="")
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.SCHEDULED
    )
    sequence_number = models.IntegerField(default=1)
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "meeting_followups"
        ordering = ["sequence_number", "follow_up_date"]

    def __str__(self):
        return f"Follow-up #{self.sequence_number} for {self.meeting_id}"
