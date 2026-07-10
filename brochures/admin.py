from django.contrib import admin
from django.utils.html import format_html
from import_export.admin import ImportExportModelAdmin

from brochures.file_metadata import apply_upload_metadata
from brochures.forms import BrochureAdminForm
from brochures.models import Brochure, BrochureCategory, BrochureSync, SavedBrochure
from brochures.storage import save_uploaded_file


@admin.register(BrochureCategory)
class BrochureCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "color", "is_active", "created_at")
    search_fields = ("name",)


@admin.register(Brochure)
class BrochureAdmin(ImportExportModelAdmin):
    form = BrochureAdminForm
    list_display = (
        "title",
        "category_name",
        "status",
        "file_link",
        "pages",
        "view_count",
        "download_count",
        "uploaded_by",
        "created_at",
    )
    list_filter = ("status", "is_public", "category_ref")
    search_fields = ("title", "category", "file_name")
    readonly_fields = (
        "id",
        "file_details",
        "view_count",
        "download_count",
        "created_at",
        "updated_at",
    )
    autocomplete_fields = ("category_ref",)
    actions = ["archive_brochures"]

    fieldsets = (
        (
            None,
            {
                "fields": (
                    "title",
                    "category_ref",
                    "description",
                    "status",
                    "is_public",
                    "tags",
                    "version",
                )
            },
        ),
        (
            "Brochure file",
            {
                "description": "Upload a PDF or ZIP. File URL, name, type, size, pages, thumbnail, and ownership are set automatically.",
                "fields": ("upload_file", "file_details"),
            },
        ),
        (
            "Stats",
            {
                "fields": ("view_count", "download_count", "id", "created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )

    @admin.display(description="File")
    def file_link(self, obj):
        if not obj.file_url:
            return "—"
        return format_html('<a href="{}" target="_blank">{}</a>', obj.file_url, obj.file_name or "Download")

    @admin.display(description="File details (auto-filled)")
    def file_details(self, obj):
        if not obj.pk:
            return "Saved automatically when you upload a file and click Save."

        thumb = obj.thumbnail_url or "—"
        if obj.thumbnail_url:
            thumb = format_html(
                '<a href="{}" target="_blank">{}</a>',
                obj.thumbnail_url,
                obj.thumbnail_url,
            )

        return format_html(
            "<table style='border-collapse:collapse'>"
            "<tr><td style='padding:4px 12px 4px 0;font-weight:600'>File URL</td>"
            "<td style='padding:4px 0'><a href='{url}' target='_blank'>{url}</a></td></tr>"
            "<tr><td style='padding:4px 12px 4px 0;font-weight:600'>File name</td><td>{name}</td></tr>"
            "<tr><td style='padding:4px 12px 4px 0;font-weight:600'>File type</td><td>{ftype}</td></tr>"
            "<tr><td style='padding:4px 12px 4px 0;font-weight:600'>File size</td><td>{fsize}</td></tr>"
            "<tr><td style='padding:4px 12px 4px 0;font-weight:600'>Pages</td><td>{pages}</td></tr>"
            "<tr><td style='padding:4px 12px 4px 0;font-weight:600'>Thumbnail</td><td>{thumb}</td></tr>"
            "<tr><td style='padding:4px 12px 4px 0;font-weight:600'>Uploaded by</td><td>{uploaded}</td></tr>"
            "<tr><td style='padding:4px 12px 4px 0;font-weight:600'>Assigned by</td><td>{assigned}</td></tr>"
            "</table>",
            url=obj.file_url or "—",
            name=obj.file_name or "—",
            ftype=obj.file_type or "—",
            fsize=obj.file_size or "—",
            pages=obj.pages if obj.pages is not None else "—",
            thumb=thumb,
            uploaded=obj.uploaded_by.full_name if obj.uploaded_by else "—",
            assigned=obj.assigned_by.full_name if obj.assigned_by else "—",
        )

    def save_model(self, request, obj, form, change):
        upload = form.cleaned_data.get("upload_file")
        if upload:
            obj.file_url = save_uploaded_file(upload, "brochures")
            apply_upload_metadata(obj, upload)

        obj.uploaded_by = request.user
        obj.assigned_by = request.user

        if obj.category_ref_id:
            obj.category = obj.category_ref.name

        super().save_model(request, obj, form, change)

    @admin.action(description="Archive selected brochures")
    def archive_brochures(self, request, queryset):
        queryset.update(status="archived")


@admin.register(SavedBrochure)
class SavedBrochureAdmin(admin.ModelAdmin):
    list_display = ("mr", "brochure_id", "custom_title", "is_deleted", "saved_at", "last_accessed")
    list_filter = ("is_deleted", "mr")
    search_fields = ("mr__email", "brochure_id", "custom_title")
    readonly_fields = ("id", "saved_at", "last_accessed", "is_deleted")

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if "is_deleted__exact" in request.GET:
            return qs
        return qs.filter(is_deleted=False)


@admin.register(BrochureSync)
class BrochureSyncAdmin(admin.ModelAdmin):
    list_display = ("mr", "brochure_id", "brochure_title", "is_deleted", "last_modified")
    list_filter = ("is_deleted", "mr")
    search_fields = ("mr__email", "brochure_id")
    readonly_fields = ("id", "created_at", "last_modified", "is_deleted")

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if "is_deleted__exact" in request.GET:
            return qs
        return qs.filter(is_deleted=False)
