import json

from django.contrib import admin
from django.utils.html import format_html
from import_export.admin import ExportMixin

from activity.models import ActivityLog, SystemSetting

# Documented activity types the mobile app pushes. Free-text is still accepted.
KNOWN_ACTIVITY_TYPES = [
    "doctor_added",
    "doctor_updated",
    "doctor_deleted",
    "meeting_scheduled",
    "meeting_updated",
    "meeting_deleted",
    "follow_up_added",
    "follow_up_updated",
    "follow_up_deleted",
    "slide_note_added",
    "slide_note_updated",
    "slide_note_deleted",
    "general_note_added",
    "general_note_updated",
    "general_note_deleted",
    "brochure_saved",
    "brochure_download",
    "brochure_renamed",
    "brochure_delete",
    "brochure_view",
    "slide_added",
    "slide_deleted",
    "slide_renamed",
    "group_created",
    "group_renamed",
    "group_deleted",
    "group_slides_added",
    "group_slides_removed",
]


class ActivityTypeListFilter(admin.SimpleListFilter):
    title = "activity type"
    parameter_name = "activity_type"

    def lookups(self, request, model_admin):
        known = [(t, t) for t in KNOWN_ACTIVITY_TYPES]
        existing = (
            ActivityLog.objects.exclude(activity_type="")
            .values_list("activity_type", flat=True)
            .distinct()
            .order_by("activity_type")
        )
        known_set = set(KNOWN_ACTIVITY_TYPES)
        extras = [(t, t) for t in existing if t not in known_set]
        return known + extras

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(activity_type=self.value())
        return queryset


@admin.register(ActivityLog)
class ActivityLogAdmin(ExportMixin, admin.ModelAdmin):
    list_display = (
        "created_at",
        "mr_display",
        "activity_type",
        "description_short",
        "entity_type",
        "entity_id",
    )
    list_filter = (ActivityTypeListFilter, "entity_type", "user", "created_at")
    search_fields = (
        "description",
        "action",
        "activity_type",
        "entity_type",
        "user__email",
        "user__first_name",
        "user__last_name",
    )
    date_hierarchy = "created_at"
    autocomplete_fields = ("user",)
    readonly_fields = (
        "id",
        "user",
        "action",
        "activity_type",
        "entity_type",
        "entity_id",
        "description",
        "metadata_pretty",
        "details_pretty",
        "ip_address",
        "user_agent",
        "created_at",
    )
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "user",
                    "activity_type",
                    "action",
                    "description",
                    "entity_type",
                    "entity_id",
                    "created_at",
                )
            },
        ),
        (
            "Metadata",
            {"fields": ("metadata_pretty", "details_pretty")},
        ),
        (
            "Request",
            {
                "classes": ("collapse",),
                "fields": ("ip_address", "user_agent", "id"),
            },
        ),
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    @admin.display(description="MR", ordering="user__email")
    def mr_display(self, obj):
        if not obj.user:
            return "System"
        name = obj.user.full_name
        return f"{name} ({obj.user.email})" if name else obj.user.email

    @admin.display(description="Description")
    def description_short(self, obj):
        text = obj.description or ""
        return (text[:100] + "…") if len(text) > 100 else text

    @admin.display(description="Metadata")
    def metadata_pretty(self, obj):
        return self._pretty_json(obj.metadata)

    @admin.display(description="Details")
    def details_pretty(self, obj):
        return self._pretty_json(obj.details)

    def _pretty_json(self, value):
        if not value:
            return "—"
        try:
            text = json.dumps(value, indent=2, default=str)
        except (TypeError, ValueError):
            text = str(value)
        return format_html(
            "<pre style='white-space:pre-wrap;max-width:70ch;margin:0'>{}</pre>",
            text,
        )


@admin.register(SystemSetting)
class SystemSettingAdmin(admin.ModelAdmin):
    list_display = ("setting_key", "setting_value", "description", "updated_at")
    search_fields = ("setting_key", "description")
