from django.contrib import admin
from import_export.admin import ImportExportModelAdmin

from doctors.models import Doctor, DoctorAssignment, DoctorPhoto


class DoctorAssignmentInline(admin.TabularInline):
    model = DoctorAssignment
    extra = 0
    fk_name = "doctor"
    readonly_fields = ("assigned_at",)


@admin.register(Doctor)
class DoctorAdmin(ImportExportModelAdmin):
    list_display = (
        "first_name",
        "last_name",
        "specialty",
        "hospital",
        "relationship_status",
        "meetings_count",
        "created_at",
    )
    list_filter = ("specialty", "relationship_status", "hospital")
    search_fields = ("first_name", "last_name", "email", "hospital", "specialty")
    inlines = [DoctorAssignmentInline]
    readonly_fields = ("id", "created_at", "updated_at")


@admin.register(DoctorAssignment)
class DoctorAssignmentAdmin(admin.ModelAdmin):
    list_display = ("doctor", "mr", "status", "assigned_by", "assigned_at")
    list_filter = ("status",)
    search_fields = ("doctor__first_name", "doctor__last_name", "mr__email")
    autocomplete_fields = ("doctor", "mr", "assigned_by")


@admin.register(DoctorPhoto)
class DoctorPhotoAdmin(admin.ModelAdmin):
    list_display = ("file_name", "user", "mime_type", "created_at")
    search_fields = ("file_name", "user__email")
