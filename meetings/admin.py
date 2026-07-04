from django.contrib import admin
from import_export.admin import ImportExportModelAdmin

from meetings.models import Meeting, MeetingFollowUp, MeetingSlideNote


class SlideNoteInline(admin.TabularInline):
    model = MeetingSlideNote
    extra = 0
    readonly_fields = ("created_at", "updated_at")


class FollowUpInline(admin.TabularInline):
    model = MeetingFollowUp
    extra = 0
    readonly_fields = ("created_at", "updated_at")


@admin.register(Meeting)
class MeetingAdmin(ImportExportModelAdmin):
    list_display = (
        "title",
        "mr",
        "doctor",
        "scheduled_date",
        "status",
        "follow_up_required",
    )
    list_filter = ("status", "scheduled_date", "follow_up_required")
    search_fields = ("title", "mr__email", "doctor__first_name", "doctor__last_name")
    date_hierarchy = "scheduled_date"
    inlines = [SlideNoteInline, FollowUpInline]
    readonly_fields = ("id", "created_at", "updated_at")


@admin.register(MeetingSlideNote)
class MeetingSlideNoteAdmin(admin.ModelAdmin):
    list_display = ("meeting", "slide_id", "slide_title", "slide_order", "created_at")
    list_filter = ("created_at",)
    search_fields = ("slide_title", "note_text", "meeting__title")
    readonly_fields = ("id", "created_at", "updated_at")


@admin.register(MeetingFollowUp)
class MeetingFollowUpAdmin(admin.ModelAdmin):
    list_display = (
        "meeting",
        "follow_up_date",
        "follow_up_time",
        "status",
        "sequence_number",
    )
    list_filter = ("status", "follow_up_date")
    readonly_fields = ("id", "created_at", "updated_at")
