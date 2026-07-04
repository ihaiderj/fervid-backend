from django.contrib import admin
from import_export.admin import ExportMixin

from activity.models import ActivityLog, SystemSetting


@admin.register(ActivityLog)
class ActivityLogAdmin(ExportMixin, admin.ModelAdmin):
    list_display = (
        "activity_type",
        "action",
        "user",
        "entity_type",
        "description",
        "created_at",
    )
    list_filter = ("activity_type", "entity_type", "created_at")
    search_fields = ("description", "action", "user__email")
    date_hierarchy = "created_at"
    readonly_fields = (
        "id",
        "user",
        "action",
        "activity_type",
        "entity_type",
        "entity_id",
        "description",
        "details",
        "metadata",
        "ip_address",
        "user_agent",
        "created_at",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(SystemSetting)
class SystemSettingAdmin(admin.ModelAdmin):
    list_display = ("setting_key", "setting_value", "description", "updated_at")
    search_fields = ("setting_key", "description")
