import uuid

from django.conf import settings
from django.db import models


class BrochureCategory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, default="")
    color = models.CharField(max_length=7, default="#8b5cf6")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "brochure_categories"
        verbose_name_plural = "brochure categories"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Brochure(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        INACTIVE = "inactive", "Inactive"
        ARCHIVED = "archived", "Archived"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    category = models.CharField(max_length=100, blank=True, default="")
    category_ref = models.ForeignKey(
        BrochureCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="brochures",
        db_column="category_id",
    )
    description = models.TextField(blank=True, default="")
    file_url = models.TextField()
    thumbnail_url = models.TextField(blank=True, default="")
    file_name = models.TextField(blank=True, default="")
    file_type = models.CharField(max_length=50, blank=True, default="")
    pages = models.IntegerField(null=True, blank=True)
    file_size = models.CharField(max_length=50, blank=True, default="")
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.ACTIVE
    )
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_brochures",
        db_column="assigned_by",
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="uploaded_brochures",
        db_column="uploaded_by",
    )
    is_public = models.BooleanField(default=True)
    tags = models.JSONField(default=list, blank=True)
    version = models.CharField(max_length=20, default="1.0")
    download_count = models.IntegerField(default=0)
    view_count = models.IntegerField(default=0)
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "brochures"
        ordering = ["-created_at"]

    def __str__(self):
        return self.title

    @property
    def category_name(self):
        if self.category_ref:
            return self.category_ref.name
        return self.category


class SavedBrochure(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    mr = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="saved_brochures",
        db_column="mr_id",
    )
    brochure_id = models.TextField()
    brochure_title = models.TextField(blank=True, default="")
    custom_title = models.TextField(blank=True, default="")
    original_brochure_data = models.JSONField(default=dict, blank=True)
    saved_at = models.DateTimeField(auto_now_add=True)
    last_accessed = models.DateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False)

    class Meta:
        db_table = "saved_brochures"
        unique_together = [("mr", "brochure_id")]

    def __str__(self):
        return f"{self.mr.email} - {self.brochure_id}"


class BrochureSync(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    mr = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="brochure_syncs",
        db_column="mr_id",
    )
    brochure_id = models.TextField()
    brochure_title = models.TextField(blank=True, default="")
    brochure_data = models.JSONField(default=dict, blank=True)
    last_modified = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_deleted = models.BooleanField(default=False)

    class Meta:
        db_table = "brochure_sync"
        unique_together = [("mr", "brochure_id")]

    def __str__(self):
        return f"{self.mr.email} - sync {self.brochure_id}"
