from django.contrib import admin
from django.utils.html import format_html
from import_export.admin import ImportExportModelAdmin

from brochures.storage import save_uploaded_file
from doctors.forms import DoctorAdminForm
from doctors.models import Doctor, DoctorAssignment, DoctorPhoto
from doctors.profile_image import profile_image_preview_html


class DoctorAssignmentInline(admin.TabularInline):
    model = DoctorAssignment
    extra = 0
    fk_name = "doctor"
    fields = ("mr", "assigned_by", "status", "transferred_at", "notes", "assigned_at")
    readonly_fields = ("assigned_by", "assigned_at")
    autocomplete_fields = ("mr",)


@admin.register(Doctor)
class DoctorAdmin(ImportExportModelAdmin):
    form = DoctorAdminForm
    list_display = (
        "profile_image_thumb",
        "first_name",
        "last_name",
        "specialty",
        "hospital",
        "created_by_display",
        "relationship_status",
        "meetings_count",
        "is_deleted",
        "created_at",
    )
    list_filter = ("is_deleted", "specialty", "relationship_status", "hospital", "created_by")
    search_fields = (
        "first_name",
        "last_name",
        "email",
        "hospital",
        "specialty",
        "created_by__email",
        "created_by__first_name",
        "created_by__last_name",
    )
    autocomplete_fields = ()
    inlines = [DoctorAssignmentInline]
    readonly_fields = (
        "id",
        "profile_image_preview",
        "created_by",
        "slide_groups_panel",
        "meetings_panel",
        "created_at",
        "updated_at",
    )

    fieldsets = (
        (
            None,
            {
                "fields": (
                    "first_name",
                    "last_name",
                    "email",
                    "phone",
                    "specialty",
                    "hospital",
                    "location",
                )
            },
        ),
        (
            "Profile photo",
            {
                "description": "Upload a photo here, or set profile_image_url via the mobile app after upload.",
                "fields": ("upload_profile_image", "profile_image_preview"),
            },
        ),
        (
            "Other",
            {
                "fields": (
                    "notes",
                    "relationship_status",
                    "meetings_count",
                    "last_meeting_date",
                    "next_appointment",
                    "created_by",
                    "is_deleted",
                    "id",
                    "created_at",
                    "updated_at",
                ),
            },
        ),
        (
            "Slide groups (from brochure sync)",
            {
                "description": (
                    "Groups whose doctorId matches this doctor's server id, "
                    "or whose name matches this doctor (e.g. \"Askari Haider\")."
                ),
                "fields": ("slide_groups_panel",),
            },
        ),
        (
            "Meetings with this doctor",
            {
                "description": "All non-deleted meetings linked to this doctor.",
                "fields": ("meetings_panel",),
            },
        ),
    )

    @admin.display(description="Photo")
    def profile_image_thumb(self, obj):
        return profile_image_preview_html(obj.profile_image_url, max_height=40)

    @admin.display(description="Current photo")
    def profile_image_preview(self, obj):
        if not obj.pk:
            return "Upload a photo and save."
        return profile_image_preview_html(obj.profile_image_url, max_height=120)

    @admin.display(description="Created by", ordering="created_by__email")
    def created_by_display(self, obj):
        if obj.created_by:
            name = obj.created_by.full_name
            if name:
                return format_html("{}<br><span style='color:#666'>{}</span>", name, obj.created_by.email)
            return obj.created_by.email

        assignment = (
            obj.assignments.filter(status="active").select_related("mr").first()
        )
        if assignment and assignment.mr:
            name = assignment.mr.full_name
            if name:
                return format_html(
                    "{}<br><span style='color:#666'>{} (assigned MR)</span>",
                    name,
                    assignment.mr.email,
                )
            return f"{assignment.mr.email} (assigned MR)"
        return "—"

    def save_model(self, request, obj, form, change):
        upload = form.cleaned_data.get("upload_profile_image")
        if upload:
            obj.profile_image_url = save_uploaded_file(upload, "doctor_photos")

        if not obj.created_by_id:
            obj.created_by = request.user

        super().save_model(request, obj, form, change)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if "is_deleted__exact" in request.GET:
            return qs
        return qs.filter(is_deleted=False)

    @admin.display(description="Slide groups")
    def slide_groups_panel(self, obj):
        from django.utils.safestring import mark_safe

        from brochures.slide_preview import find_groups_for_doctor

        items = find_groups_for_doctor(obj)
        if not items:
            return mark_safe(
                "<p style='color:#666'>No slide groups linked to this doctor yet. "
                "Groups match by <code>doctorId</code> (server UUID) or by group name "
                "(e.g. &quot;Askari Haider&quot;).</p>"
            )

        rows = []
        for item in items:
            group = item["group"]
            sync = item["sync"]
            slide_ids = group.get("slideIds") or group.get("slide_ids") or []
            color = group.get("color") or "#ccc"
            rows.append(
                format_html(
                    "<tr>"
                    "<td style='padding:8px'>"
                    "<span style='display:inline-block;width:12px;height:12px;"
                    "border-radius:2px;background:{};margin-right:6px'></span>"
                    "<strong>{}</strong></td>"
                    "<td style='padding:8px'>{}</td>"
                    "<td style='padding:8px'>"
                    "<a href='/admin/brochures/brochuresync/{}/change/'>{}</a>"
                    "<br><span style='color:#999;font-size:11px'>{}</span></td>"
                    "<td style='padding:8px'>{}</td>"
                    "<td style='padding:8px;font-size:12px'>{}</td>"
                    "</tr>",
                    color,
                    group.get("name") or "—",
                    group.get("doctorId") or group.get("doctor_id") or "—",
                    sync.id,
                    sync.brochure_title or sync.brochure_id,
                    sync.mr.email if sync.mr_id else "",
                    len(slide_ids),
                    ", ".join(slide_ids[:8]) + ("…" if len(slide_ids) > 8 else ""),
                )
            )
        return mark_safe(
            "<table style='border-collapse:collapse;width:100%;max-width:1000px'>"
            "<thead><tr style='background:#f0f0f0'>"
            "<th style='padding:8px;text-align:left'>Group</th>"
            "<th style='padding:8px;text-align:left'>Doctor id</th>"
            "<th style='padding:8px;text-align:left'>Brochure sync</th>"
            "<th style='padding:8px;text-align:left'># slides</th>"
            "<th style='padding:8px;text-align:left'>Slide ids</th>"
            "</tr></thead><tbody>"
            + "".join(str(r) for r in rows)
            + "</tbody></table>"
        )

    @admin.display(description="Meetings")
    def meetings_panel(self, obj):
        from django.utils.safestring import mark_safe

        from meetings.models import Meeting

        meetings = (
            Meeting.objects.filter(doctor=obj, is_deleted=False)
            .select_related("mr")
            .order_by("-scheduled_date")
        )
        if not meetings.exists():
            return mark_safe("<p style='color:#666'>No meetings for this doctor.</p>")

        rows = []
        for m in meetings:
            rows.append(
                format_html(
                    "<tr>"
                    "<td style='padding:8px'>"
                    "<a href='/admin/meetings/meeting/{}/change/'><strong>{}</strong></a></td>"
                    "<td style='padding:8px'>{}</td>"
                    "<td style='padding:8px'>{}</td>"
                    "<td style='padding:8px'>{}</td>"
                    "<td style='padding:8px'>{}</td>"
                    "</tr>",
                    m.id,
                    m.title,
                    m.mr.email if m.mr_id else "—",
                    m.scheduled_date.strftime("%Y-%m-%d %H:%M") if m.scheduled_date else "—",
                    m.status,
                    m.purpose or "—",
                )
            )
        return mark_safe(
            "<table style='border-collapse:collapse;width:100%;max-width:1000px'>"
            "<thead><tr style='background:#f0f0f0'>"
            "<th style='padding:8px;text-align:left'>Meeting</th>"
            "<th style='padding:8px;text-align:left'>MR</th>"
            "<th style='padding:8px;text-align:left'>Scheduled</th>"
            "<th style='padding:8px;text-align:left'>Status</th>"
            "<th style='padding:8px;text-align:left'>Purpose</th>"
            "</tr></thead><tbody>"
            + "".join(str(r) for r in rows)
            + "</tbody></table>"
        )


@admin.register(DoctorAssignment)
class DoctorAssignmentAdmin(admin.ModelAdmin):
    list_display = ("doctor", "mr", "status", "assigned_by", "assigned_at")
    list_filter = ("status",)
    search_fields = ("doctor__first_name", "doctor__last_name", "mr__email")
    autocomplete_fields = ("doctor", "mr", "assigned_by")


@admin.register(DoctorPhoto)
class DoctorPhotoAdmin(admin.ModelAdmin):
    list_display = ("file_name", "photo_thumb", "user", "mime_type", "created_at")
    search_fields = ("file_name", "user__email")
    readonly_fields = ("photo_preview",)

    @admin.display(description="Photo")
    def photo_thumb(self, obj):
        return profile_image_preview_html(obj.file_path, max_height=40)

    @admin.display(description="Preview")
    def photo_preview(self, obj):
        return profile_image_preview_html(obj.file_path, max_height=120)
