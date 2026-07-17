from doctors.models import Doctor
from meetings.models import Meeting


def refresh_doctor_meetings_count(doctor_id):
    """Keep Doctor.meetings_count in sync with non-deleted meetings."""
    if not doctor_id:
        return
    count = Meeting.objects.filter(doctor_id=doctor_id, is_deleted=False).count()
    Doctor.objects.filter(id=doctor_id).update(meetings_count=count)


def refresh_meeting_presentation_slides(meeting):
    """
    Derive Meeting.presentation_slides from its slide notes so it can't drift.

    Blank ({}) when there are no notes. Otherwise a dict with the primary
    brochure at the top level plus the full list of unique brochures used:
        {
          "brochure_id": "<first>",
          "brochure_title": "<first custom title>",
          "brochures": [{"brochure_id": ..., "brochure_title": ...}, ...],
        }
    """
    if meeting is None:
        return

    notes = meeting.slide_notes.filter(is_deleted=False).order_by(
        "slide_order", "created_at"
    )

    brochures = []
    seen = set()
    for note in notes:
        brochure_id = (note.brochure_id or "").strip()
        brochure_title = (note.brochure_title or "").strip()
        if not brochure_id and not brochure_title:
            continue
        key = (brochure_id, brochure_title)
        if key in seen:
            continue
        seen.add(key)
        brochures.append(
            {"brochure_id": brochure_id, "brochure_title": brochure_title}
        )

    if not brochures:
        presentation_slides = {}
    else:
        primary = brochures[0]
        presentation_slides = {
            "brochure_id": primary["brochure_id"],
            "brochure_title": primary["brochure_title"],
            "brochures": brochures,
        }

    Meeting.objects.filter(id=meeting.id).update(
        presentation_slides=presentation_slides
    )
    meeting.presentation_slides = presentation_slides
    return presentation_slides
