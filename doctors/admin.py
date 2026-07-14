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
    readonly_fields = ("assigned_at",)


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
    autocomplete_fields = ("created_by",)
    inlines = [DoctorAssignmentInline]
    readonly_fields = ("id", "profile_image_preview", "created_at", "updated_at")

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
