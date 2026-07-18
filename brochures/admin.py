from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
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
    list_display = (
        "mr",
        "custom_title",
        "source_brochure",
        "brochure_id",
        "is_deleted",
        "saved_at",
        "last_accessed",
    )
    list_filter = ("is_deleted", "mr")
    search_fields = ("mr__email", "brochure_id", "custom_title", "brochure_title")
    readonly_fields = (
        "id",
        "source_brochure",
        "slides_panel",
        "groups_panel",
        "slide_notes_panel",
        "sync_link_hint",
        "saved_at",
        "last_accessed",
    )
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "mr",
                    "brochure_id",
                    "brochure_title",
                    "custom_title",
                    "source_brochure",
                    "original_brochure_data",
                    "id",
                    "saved_at",
                    "last_accessed",
                    "is_deleted",
                )
            },
        ),
        (
            "Slides (with preview)",
            {
                "description": "Previews come from the source brochure ZIP or from server image_url in brochure_sync.",
                "fields": ("sync_link_hint", "slides_panel"),
            },
        ),
        (
            "Groups",
            {"fields": ("groups_panel",)},
        ),
        (
            "Slide notes",
            {
                "description": (
                    "Previews and renamed slide titles come from brochure_sync. "
                    "Use Edit / Delete to change or soft-delete a note."
                ),
                "fields": ("slide_notes_panel",),
            },
        ),
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if "is_deleted__exact" in request.GET:
            return qs
        return qs.filter(is_deleted=False)

    def delete_model(self, request, obj):
        from core.soft_delete import soft_delete_instance

        soft_delete_instance(obj, "last_accessed")

    def delete_queryset(self, request, queryset):
        from core.soft_delete import soft_delete_instance

        for obj in queryset:
            soft_delete_instance(obj, "last_accessed")

    @admin.display(description="Source brochure")
    def source_brochure(self, obj):
        from django.utils.html import format_html

        brochure = Brochure.objects.filter(id=obj.brochure_id).first()
        if not brochure:
            return obj.brochure_title or "—"
        return format_html(
            '<a href="/admin/brochures/brochure/{}/change/">{}</a>',
            brochure.id,
            brochure.title,
        )

    def _source(self, obj):
        return Brochure.objects.filter(id=obj.brochure_id).first()

    def _matched_sync(self, obj):
        from brochures.slide_preview import find_brochure_syncs_for_saved

        syncs = find_brochure_syncs_for_saved(obj)
        return syncs[0] if syncs else None

    @admin.display(description="Brochure sync link")
    def sync_link_hint(self, obj):
        from django.utils.html import format_html

        from brochures.slide_preview import find_brochure_syncs_for_saved, find_all_syncs_for_mr

        syncs = find_brochure_syncs_for_saved(obj)
        if syncs:
            s = syncs[0]
            return format_html(
                'Linked to brochure sync <a href="/admin/brochures/brochuresync/{}/change/">'
                "{}</a> (id={})",
                s.id,
                s.brochure_title or s.brochure_id,
                s.brochure_id,
            )
        others = find_all_syncs_for_mr(obj.mr)
        if not others:
            return format_html(
                "<span style='color:#a00'>No brochure_sync row for this MR. "
                "App must push brochure_sync with brochure_id = this saved brochure's server id.</span>"
            )
        links = "".join(
            format_html(
                '<li><a href="/admin/brochures/brochuresync/{}/change/">{}</a> '
                "(sync id={}, title={}) — not linked to this saved copy</li>",
                s.id,
                s.brochure_id,
                s.brochure_id,
                s.brochure_title or "—",
            )
            for s in others
        )
        return format_html(
            "<div style='padding:10px;background:#fff8e1;border:1px solid #f0c36d;"
            "border-radius:4px;max-width:70ch'>"
            "<strong>Sync not linked to this saved copy yet.</strong><br>"
            "Slides below are from the <em>source</em> brochure ZIP (previews work). "
            "Groups/custom order appear after the app pushes "
            "<code>brochure_sync</code> with "
            "<code>brochure_id = {}</code> and "
            "<code>brochure_title = {}</code>."
            "<ul style='margin:8px 0 0 16px'>{}</ul>"
            "</div>",
            obj.id,
            obj.custom_title or obj.brochure_title or "—",
            mark_safe(links),
        )

    @admin.display(description="Slides")
    def slides_panel(self, obj):
        from brochures.slide_preview import (
            render_slides_table,
            sync_payload,
            find_slide_notes_for_saved,
            slide_image_url_from_filename,
        )

        source = self._source(obj)
        sync = self._matched_sync(obj)
        slides = []
        if sync:
            slides = sync_payload(sync)["slides"]
        elif source:
            # Fall back to source ZIP slide list for preview.
            from brochures.slide_preview import ensure_source_slides_extracted

            dest = ensure_source_slides_extracted(source)
            if dest:
                files = sorted(
                    [p.name for p in dest.iterdir() if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}]
                )
                slides = [
                    {
                        "id": f"source_slide_{i}",
                        "title": name,
                        "fileName": name,
                        "order": i,
                        "image_url": slide_image_url_from_filename(source, name),
                    }
                    for i, name in enumerate(files, start=1)
                ]

        notes = find_slide_notes_for_saved(obj)
        notes_by_slide = {}
        for n in notes:
            notes_by_slide.setdefault(n.slide_id, []).append(
                {
                    "meeting": n.meeting.title if n.meeting_id else "",
                    "text": n.note_text or "",
                }
            )
        return render_slides_table(slides, source_brochure=source, notes_by_slide=notes_by_slide)

    @admin.display(description="Groups")
    def groups_panel(self, obj):
        from brochures.slide_preview import render_groups_table, sync_payload

        sync = self._matched_sync(obj)
        if not sync:
            return mark_safe(
                "<p style='color:#666'>No linked brochure_sync — groups appear once "
                "the app pushes sync with this saved brochure's server id.</p>"
            )
        payload = sync_payload(sync)
        return render_groups_table(
            payload["groups"],
            payload["slides"],
            source_brochure=self._source(obj),
        )

    @admin.display(description="Slide notes")
    def slide_notes_panel(self, obj):
        from brochures.slide_preview import find_slide_notes_for_saved, render_notes_table

        return render_notes_table(find_slide_notes_for_saved(obj))


@admin.register(BrochureSync)
class BrochureSyncAdmin(admin.ModelAdmin):
    list_display = (
        "mr",
        "brochure_title",
        "brochure_id",
        "slides_count",
        "groups_count",
        "is_deleted",
        "last_modified",
    )
    list_filter = ("is_deleted", "mr")
    search_fields = ("mr__email", "brochure_id", "brochure_title")
    readonly_fields = (
        "id",
        "brochure_data_preview",
        "created_at",
        "last_modified",
        "is_deleted",
    )
    fields = (
        "mr",
        "brochure_id",
        "brochure_title",
        "brochure_data_preview",
        "is_deleted",
        "created_at",
        "last_modified",
        "id",
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if "is_deleted__exact" in request.GET:
            return qs
        return qs.filter(is_deleted=False)

    def _data(self, obj):
        return obj.brochure_data if isinstance(obj.brochure_data, dict) else {}

    @admin.display(description="Slides")
    def slides_count(self, obj):
        slides = self._data(obj).get("slides") or []
        return len(slides) if isinstance(slides, list) else 0

    @admin.display(description="Groups")
    def groups_count(self, obj):
        data = self._data(obj)
        groups = data.get("groups") or data.get("slide_groups") or []
        return len(groups) if isinstance(groups, list) else 0

    @admin.display(description="Brochure data (customizations)")
    def brochure_data_preview(self, obj):
        import json

        from django.utils.html import format_html

        data = self._data(obj)
        if not data:
            return "— (no customizations)"
        text = json.dumps(data, indent=2, default=str)
        return format_html(
            "<pre style='white-space:pre-wrap;max-width:80ch;max-height:400px;"
            "overflow:auto;margin:0'>{}</pre>",
            text,
        )
