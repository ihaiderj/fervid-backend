import uuid

from django.conf import settings
from django.db import models


class ActivityLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="activity_logs",
        db_column="user_id",
    )
    action = models.CharField(max_length=100, blank=True, default="")
    activity_type = models.CharField(max_length=100, blank=True, default="")
    entity_type = models.CharField(max_length=50, blank=True, default="")
    entity_id = models.UUIDField(null=True, blank=True)
    description = models.TextField(blank=True, default="")
    details = models.JSONField(default=dict, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, default="")
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "activity_logs"
        ordering = ["-created_at"]

    def __str__(self):
        label = self.activity_type or self.action
        return f"{label} by {self.user_id}"


class SystemSetting(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    setting_key = models.CharField(max_length=100, unique=True)
    setting_value = models.TextField()
    description = models.TextField(blank=True, default="")
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="settings_updated",
        db_column="updated_by",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "system_settings"

    def __str__(self):
        return self.setting_key
