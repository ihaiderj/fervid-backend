import uuid

from django.conf import settings
from django.db import models


class Doctor(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(max_length=255, blank=True, default="")
    phone = models.CharField(max_length=20, blank=True, default="")
    specialty = models.CharField(max_length=100)
    hospital = models.CharField(max_length=255)
    location = models.CharField(max_length=255, blank=True, default="")
    profile_image_url = models.TextField(blank=True, default="")
    notes = models.TextField(blank=True, default="")
    relationship_status = models.CharField(max_length=50, default="active")
    meetings_count = models.IntegerField(default=0)
    last_meeting_date = models.DateTimeField(null=True, blank=True)
    next_appointment = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_doctors",
        db_column="created_by",
    )
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "doctors"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Dr. {self.first_name} {self.last_name}"


class DoctorAssignment(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        INACTIVE = "inactive", "Inactive"
        TRANSFERRED = "transferred", "Transferred"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    doctor = models.ForeignKey(
        Doctor, on_delete=models.CASCADE, related_name="assignments", db_column="doctor_id"
    )
    mr = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="doctor_assignments",
        db_column="mr_id",
    )
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="assignments_made",
        db_column="assigned_by",
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.ACTIVE
    )
    assigned_at = models.DateTimeField(auto_now_add=True)
    transferred_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True, default="")

    class Meta:
        db_table = "doctor_assignments"
        unique_together = [("doctor", "mr", "status")]

    def __str__(self):
        return f"{self.doctor} -> {self.mr.email}"


class DoctorPhoto(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="doctor_photos",
        db_column="user_id",
    )
    file_name = models.TextField()
    file_path = models.TextField(blank=True, default="")
    photo_data = models.TextField(blank=True, default="")
    mime_type = models.CharField(max_length=100, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "doctor_photos"

    def __str__(self):
        return self.file_name
