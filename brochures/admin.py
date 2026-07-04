from django.contrib import admin
from import_export.admin import ImportExportModelAdmin

from brochures.models import Brochure, BrochureCategory, BrochureSync, SavedBrochure


@admin.register(BrochureCategory)
class BrochureCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "color", "is_active", "created_at")
    search_fields = ("name",)


@admin.register(Brochure)
class BrochureAdmin(ImportExportModelAdmin):
    list_display = (
        "title",
        "category_name",
        "status",
        "view_count",
        "download_count",
        "uploaded_by",
        "created_at",
    )
    list_filter = ("status", "is_public", "category_ref")
    search_fields = ("title", "category", "file_name")
    readonly_fields = ("id", "view_count", "download_count", "created_at", "updated_at")
    actions = ["archive_brochures"]

    @admin.action(description="Archive selected brochures")
    def archive_brochures(self, request, queryset):
        queryset.update(status="archived")


@admin.register(SavedBrochure)
class SavedBrochureAdmin(admin.ModelAdmin):
    list_display = ("mr", "brochure_id", "custom_title", "saved_at", "last_accessed")
    search_fields = ("mr__email", "brochure_id", "custom_title")
    readonly_fields = ("id", "saved_at", "last_accessed")


@admin.register(BrochureSync)
class BrochureSyncAdmin(admin.ModelAdmin):
    list_display = ("mr", "brochure_id", "brochure_title", "last_modified")
    search_fields = ("mr__email", "brochure_id")
    readonly_fields = ("id", "created_at", "last_modified")
