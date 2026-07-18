import uuid

from django.contrib import admin
from django.db import models
from django.forms import BaseInlineFormSet, Textarea, TextInput
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from import_export.admin import ImportExportModelAdmin

from meetings.models import Meeting, MeetingFollowUp, MeetingNote, MeetingSlideNote

# Taller, narrower text inputs so the change form never scrolls sideways.
NARROW_TEXT_OVERRIDES = {
    models.TextField: {
        "widget": Textarea(attrs={"rows": 4, "style": "width:60ch;max-width:100%"})
    },
    models.CharField: {
        "widget": TextInput(attrs={"style": "width:40ch;max-width:100%"})
    },
}


def resolve_brochure_title(brochure_id, brochure_title=""):
    """
    Best-effort human title for a brochure id, checked in priority order:
      1. title stored on the note itself
      2. saved-brochure copy matched by its own id (savedBrochureDbId)
      3. saved-brochure copy matched by source brochure_id
      4. source admin brochure title
    Returns "" when the id is unknown to the server (e.g. an unsynced device id).
    """
    if brochure_title:
        return brochure_title

    from brochures.models import Brochure, SavedBrochure

    is_uuid = True
    try:
        uuid.UUID(str(brochure_id))
    except (ValueError, TypeError, AttributeError):
        is_uuid = False

    if is_uuid:
        saved_by_pk = (
            SavedBrochure.objects.filter(id=brochure_id)
            .exclude(custom_title="")
            .first()
        )
        if saved_by_pk:
            return saved_by_pk.custom_title

    saved = (
        SavedBrochure.objects.filter(brochure_id=str(brochure_id))
        .exclude(custom_title="")
        .first()
    )
    if saved:
        return saved.custom_title

    if is_uuid:
        brochure = Brochure.objects.filter(id=brochure_id).first()
        if brochure:
            return brochure.title
    return ""


def brochure_display_html(obj):
    """Resolved brochure title + id for a slide note, with a hint when unresolved."""
    title = resolve_brochure_title(obj.brochure_id, obj.brochure_title)
    if title:
        return format_html(
            "<strong>{}</strong> <span style='color:#666'>({})</span>",
            title,
            obj.brochure_id or "\u2014",
        )
    if obj.brochure_id:
        return format_html(
            "<span style='color:#a00'>no title</span> "
            "<span style='color:#666'>({})</span><br>"
            "<span style='color:#999;font-size:11px'>This brochure id is not on the "
            "server yet \u2014 the app must send <code>brochure_title</code> (or sync "
            "the saved brochure) for the title to appear.</span>",
            obj.brochure_id,
        )
    return "\u2014"


class SoftDeleteSlideNoteFormSet(BaseInlineFormSet):
    def delete_existing(self, obj, commit=True):
        if commit:
            from core.soft_delete import soft_delete_instance

            soft_delete_instance(obj, "updated_at")


class SlideNoteInline(admin.StackedInline):
    model = MeetingSlideNote
    extra = 0
    formset = SoftDeleteSlideNoteFormSet
    formfield_overrides = {
        models.TextField: {
            "widget": Textarea(attrs={"rows": 3, "style": "width:60ch;max-width:100%"})
        },
    }
    fields = (
        "slide_preview",
        "slide_display_name",
        "slide_order",
        "slide_title",
        "slide_id",
        "brochure_id",
        "brochure_title",
        "brochure_resolved",
        "note_text",
    )
    readonly_fields = ("slide_preview", "slide_display_name", "brochure_resolved")

    def get_queryset(self, request):
        return super().get_queryset(request).filter(is_deleted=False)

    @admin.display(description="Brochure (resolved)")
    def brochure_resolved(self, obj):
        return brochure_display_html(obj)

    @admin.display(description="Slide preview")
    def slide_preview(self, obj):
        if not obj or not obj.pk:
            return "—"
        from brochures.slide_preview import resolve_note_slide_image_url, thumb_html
        from brochures.slide_preview import resolve_note_slide_display_title

        return thumb_html(
            resolve_note_slide_image_url(obj),
            resolve_note_slide_display_title(obj),
        )

    @admin.display(description="Slide name (from brochure/group)")
    def slide_display_name(self, obj):
        if not obj or not obj.pk:
            return "—"
        from brochures.slide_preview import resolve_note_slide_display_title

        return resolve_note_slide_display_title(obj)

class GeneralNoteInline(admin.StackedInline):
    model = MeetingNote
    extra = 0
    verbose_name = "General meeting note"
    verbose_name_plural = "General meeting notes"
    formfield_overrides = {
        models.TextField: {
            "widget": Textarea(attrs={"rows": 3, "style": "width:60ch;max-width:100%"})
        },
    }
    fields = ("title", "notes")

    def get_queryset(self, request):
        return super().get_queryset(request).filter(is_deleted=False)


class FollowUpInline(admin.StackedInline):
    model = MeetingFollowUp
    extra = 0
    formfield_overrides = {
        models.TextField: {
            "widget": Textarea(attrs={"rows": 3, "style": "width:60ch;max-width:100%"})
        },
    }
    fields = (
        "sequence_number",
        "follow_up_date",
        "follow_up_time",
        "status",
        "follow_up_notes",
    )
    readonly_fields = ("created_at", "updated_at")


@admin.register(Meeting)
class MeetingAdmin(ImportExportModelAdmin):
    formfield_overrides = NARROW_TEXT_OVERRIDES
    list_display = (
        "title",
        "mr",
        "doctor",
        "scheduled_date",
        "status",
        "next_follow_up",
        "brochures_used",
        "is_deleted",
    )
    list_filter = ("status", "is_deleted", "scheduled_date", "mr")
    search_fields = ("title", "mr__email", "doctor__first_name", "doctor__last_name")
    date_hierarchy = "scheduled_date"
    inlines = [GeneralNoteInline, SlideNoteInline, FollowUpInline]
    autocomplete_fields = ("mr", "doctor")
    readonly_fields = (
        "brochures_used",
        "presentation_slides",
        "next_follow_up",
        "created_at",
        "updated_at",
    )

    fieldsets = (
        (
            None,
            {
                "fields": (
                    "title",
                    "mr",
                    "doctor",
                    "brochure",
                    "scheduled_date",
                    "duration_minutes",
                    "status",
                    "purpose",
                    "location",
                    "notes",
                    "next_follow_up",
                    "brochures_used",
                )
            },
        ),
        (
            "Legacy follow-up (deprecated \u2014 use the follow-ups table)",
            {
                "classes": ("collapse",),
                "description": "Superseded by the Meeting follow-ups below.",
                "fields": (
                    "follow_up_required",
                    "follow_up_date",
                    "follow_up_time",
                    "follow_up_notes",
                ),
            },
        ),
        (
            "System",
            {
                "classes": ("collapse",),
                "fields": ("presentation_slides", "comments", "is_deleted", "created_at", "updated_at"),
            },
        ),
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if "is_deleted__exact" in request.GET:
            return qs
        return qs.filter(is_deleted=False)

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        from meetings.services import refresh_meeting_presentation_slides

        refresh_meeting_presentation_slides(form.instance)

    @admin.display(description="Next follow-up")
    def next_follow_up(self, obj):
        from django.utils import timezone

        fu = (
            obj.followups.filter(is_deleted=False, status="scheduled")
            .order_by("follow_up_date")
            .first()
        )
        if not fu:
            return "—"
        when = fu.follow_up_date
        label = when.strftime("%Y-%m-%d %H:%M") if when else "—"
        if when and when >= timezone.now():
            return f"{label} (pending)"
        return label

    @admin.display(description="Brochures used (from notes)")
    def brochures_used(self, obj):
        slides = obj.presentation_slides or {}
        brochures = slides.get("brochures") or []
        if not brochures and (slides.get("brochure_id") or slides.get("brochure_title")):
            brochures = [
                {
                    "brochure_id": slides.get("brochure_id", ""),
                    "brochure_title": slides.get("brochure_title", ""),
                }
            ]
        if not brochures:
            return "\u2014"

        rows = []
        for b in brochures:
            brochure_id = b.get("brochure_id", "")
            title = resolve_brochure_title(brochure_id, b.get("brochure_title", ""))
            if title and brochure_id:
                rows.append(
                    format_html(
                        "<strong>{}</strong> <span style='color:#666'>({})</span>",
                        title,
                        brochure_id,
                    )
                )
            elif title:
                rows.append(format_html("<strong>{}</strong>", title))
            elif brochure_id:
                rows.append(
                    format_html(
                        "<span style='color:#a00'>(no title)</span> "
                        "<span style='color:#666'>({})</span>",
                        brochure_id,
                    )
                )
        if not rows:
            return "\u2014"
        return mark_safe("<br>".join(str(r) for r in rows))


@admin.register(MeetingSlideNote)
class MeetingSlideNoteAdmin(admin.ModelAdmin):
    formfield_overrides = NARROW_TEXT_OVERRIDES
    list_display = (
        "meeting",
        "slide_preview_thumb",
        "slide_display_name",
        "slide_id",
        "slide_title",
        "brochure_resolved",
        "slide_order",
        "is_deleted",
        "created_at",
    )
    list_filter = ("is_deleted", "created_at")
    search_fields = ("slide_title", "brochure_title", "note_text", "meeting__title")
    readonly_fields = (
        "id",
        "slide_preview",
        "slide_display_name",
        "brochure_resolved",
        "created_at",
        "updated_at",
    )
    fields = (
        "meeting",
        "slide_preview",
        "slide_display_name",
        "slide_order",
        "slide_title",
        "slide_id",
        "brochure_id",
        "brochure_title",
        "brochure_resolved",
        "note_text",
        "is_deleted",
        "id",
        "created_at",
        "updated_at",
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if "is_deleted__exact" in request.GET:
            return qs
        return qs.filter(is_deleted=False)

    @admin.display(description="Preview")
    def slide_preview_thumb(self, obj):
        from brochures.slide_preview import (
            resolve_note_slide_display_title,
            resolve_note_slide_image_url,
            thumb_html,
        )

        return thumb_html(
            resolve_note_slide_image_url(obj),
            resolve_note_slide_display_title(obj),
            max_height=48,
        )

    @admin.display(description="Slide preview")
    def slide_preview(self, obj):
        from brochures.slide_preview import (
            resolve_note_slide_display_title,
            resolve_note_slide_image_url,
            thumb_html,
        )

        return thumb_html(
            resolve_note_slide_image_url(obj),
            resolve_note_slide_display_title(obj),
        )

    @admin.display(description="Slide name (from brochure/group)")
    def slide_display_name(self, obj):
        from brochures.slide_preview import resolve_note_slide_display_title

        return resolve_note_slide_display_title(obj)

    @admin.display(description="Brochure (resolved)")
    def brochure_resolved(self, obj):
        return brochure_display_html(obj)

    def delete_model(self, request, obj):
        from core.soft_delete import soft_delete_instance

        soft_delete_instance(obj, "updated_at")

    def delete_queryset(self, request, queryset):
        from core.soft_delete import soft_delete_instance

        for obj in queryset:
            soft_delete_instance(obj, "updated_at")


@admin.register(MeetingNote)
class MeetingNoteAdmin(admin.ModelAdmin):
    formfield_overrides = NARROW_TEXT_OVERRIDES
    list_display = ("meeting", "title", "short_notes", "is_deleted", "created_at")
    list_filter = ("is_deleted", "created_at")
    search_fields = ("title", "notes", "meeting__title")
    readonly_fields = ("id", "created_at", "updated_at")

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if "is_deleted__exact" in request.GET:
            return qs
        return qs.filter(is_deleted=False)

    @admin.display(description="Notes")
    def short_notes(self, obj):
        text = obj.notes or ""
        return (text[:80] + "\u2026") if len(text) > 80 else text


@admin.register(MeetingFollowUp)
class MeetingFollowUpAdmin(admin.ModelAdmin):
    formfield_overrides = NARROW_TEXT_OVERRIDES
    list_display = (
        "meeting",
        "follow_up_date",
        "follow_up_time",
        "status",
        "sequence_number",
    )
    list_filter = ("status", "follow_up_date")
    readonly_fields = ("id", "created_at", "updated_at")
