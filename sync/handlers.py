import uuid as uuid_mod

from django.utils import timezone

from activity.models import ActivityLog
from brochures.models import BrochureSync, SavedBrochure
from brochures.saved_brochure_service import (
    create_saved_brochure,
    get_saved_brochure_by_id,
    soft_delete_saved_brochure,
    update_saved_brochure,
)
from core.soft_delete import soft_delete_instance
from core.services import log_activity
from doctors.models import Doctor, DoctorAssignment
from doctors.doctor_service import soft_delete_doctor_for_mr
from meetings.models import Meeting, MeetingFollowUp, MeetingNote, MeetingSlideNote
from meetings.services import (
    refresh_doctor_meetings_count,
    refresh_meeting_presentation_slides,
)


def _parse_client_uuid(data):
    """Optional client-generated UUID for idempotent creates (id / client_id / local_uuid)."""
    raw = data.get("id") or data.get("client_id") or data.get("local_uuid")
    if not raw:
        return None
    try:
        return uuid_mod.UUID(str(raw))
    except (ValueError, TypeError, AttributeError):
        return None


class SyncPushHandler:
    """Process offline sync queue operations from mobile client."""

    ENTITY_ORDER = [
        "doctors",
        "meetings",
        "meeting_notes",
        "meeting_general_notes",
        "meeting_slide_notes",
        "meeting_followups",
        "saved_brochures",
        "brochure_sync",
        "activity_logs",
    ]

    def __init__(self, user):
        self.user = user
        self.results = []

    def process(self, operations):
        sorted_ops = sorted(
            operations,
            key=lambda op: self.ENTITY_ORDER.index(op.get("entity", ""))
            if op.get("entity") in self.ENTITY_ORDER
            else 999,
        )
        for op in sorted_ops:
            try:
                result = self._handle_operation(op)
                self.results.append({"id": op.get("local_id"), "success": True, **result})
            except Exception as e:
                self.results.append(
                    {
                        "id": op.get("local_id"),
                        "success": False,
                        "error": str(e),
                    }
                )
        return self.results

    def _handle_operation(self, op):
        entity = op.get("entity")
        action = op.get("action", "create")
        data = op.get("data", {})
        handler = getattr(self, f"_handle_{entity}", None)
        if not handler:
            raise ValueError(f"Unknown entity: {entity}")
        return handler(action, data)

    def _handle_doctors(self, action, data):
        if data.get("is_deleted") and action in ("create", "update", "delete"):
            if not data.get("server_id"):
                raise ValueError("server_id is required to delete doctor via sync")
            doctor = soft_delete_doctor_for_mr(self.user, data["server_id"])
            if not doctor:
                raise ValueError("Doctor not found or not accessible")
            return {"server_id": str(doctor.id)}

        if action == "create":
            client_id = _parse_client_uuid(data)
            if client_id:
                existing = Doctor.objects.filter(id=client_id).first()
                if existing:
                    # Idempotent retry of the same create.
                    DoctorAssignment.objects.get_or_create(
                        doctor=existing,
                        mr=self.user,
                        status="active",
                        defaults={"assigned_by": self.user},
                    )
                    return {"server_id": str(existing.id)}

            create_kwargs = dict(
                first_name=data["first_name"],
                last_name=data["last_name"],
                specialty=data["specialty"],
                hospital=data["hospital"],
                phone=data.get("phone", ""),
                email=data.get("email", ""),
                location=data.get("location", ""),
                notes=data.get("notes", ""),
                profile_image_url=data.get("profile_image_url", ""),
                created_by=self.user,
            )
            if client_id:
                create_kwargs["id"] = client_id

            doctor = Doctor.objects.create(**create_kwargs)
            DoctorAssignment.objects.create(
                doctor=doctor, mr=self.user, assigned_by=self.user, status="active"
            )
            return {"server_id": str(doctor.id)}
        elif action == "update":
            doctor = Doctor.objects.get(id=data["server_id"], is_deleted=False)
            if not DoctorAssignment.objects.filter(
                doctor=doctor, mr=self.user, status="active"
            ).exists() and doctor.created_by_id != self.user.id:
                raise ValueError("Doctor not found or not accessible")
            for field in (
                "first_name",
                "last_name",
                "specialty",
                "hospital",
                "phone",
                "email",
                "location",
                "notes",
                "profile_image_url",
            ):
                if field in data:
                    setattr(doctor, field, data[field])
            doctor.save()
            return {"server_id": str(doctor.id)}
        elif action == "delete":
            doctor = soft_delete_doctor_for_mr(self.user, data["server_id"])
            if not doctor:
                raise ValueError("Doctor not found or not accessible")
            return {"server_id": str(doctor.id)}
        raise ValueError(f"Unknown action: {action}")

    def _handle_meetings(self, action, data):
        if action == "create":
            client_id = _parse_client_uuid(data)
            if client_id:
                existing = Meeting.objects.filter(id=client_id, mr=self.user).first()
                if existing:
                    return {"server_id": str(existing.id)}

            brochure = None
            brochure_id = data.get("brochure_id")
            if brochure_id:
                from brochures.models import Brochure

                brochure = Brochure.objects.filter(id=brochure_id).first()

            create_kwargs = dict(
                mr=self.user,
                doctor_id=data["doctor_id"],
                brochure=brochure,
                title=data.get("title", "Meeting"),
                purpose=data.get("purpose", ""),
                scheduled_date=data.get("scheduled_date", timezone.now()),
                duration_minutes=data.get("duration_minutes", 30),
                location=data.get("location", ""),
                notes=data.get("notes", ""),
                presentation_slides={
                    "brochure_id": str(brochure_id or ""),
                    "brochure_title": data.get("brochure_title", ""),
                },
            )
            if client_id:
                create_kwargs["id"] = client_id

            meeting = Meeting.objects.create(**create_kwargs)
            refresh_doctor_meetings_count(meeting.doctor_id)
            return {"server_id": str(meeting.id)}
        elif action == "update":
            meeting = Meeting.objects.get(id=data["server_id"], mr=self.user)
            previous_doctor_id = meeting.doctor_id
            for field in (
                "title",
                "status",
                "location",
                "notes",
                "purpose",
                "scheduled_date",
                "duration_minutes",
            ):
                if field in data:
                    setattr(meeting, field, data[field])
            if "doctor_id" in data:
                meeting.doctor_id = data["doctor_id"]
            meeting.save()
            refresh_doctor_meetings_count(previous_doctor_id)
            if meeting.doctor_id != previous_doctor_id:
                refresh_doctor_meetings_count(meeting.doctor_id)
            return {"server_id": str(meeting.id)}
        elif action == "delete":
            from core.soft_delete import soft_delete_instance

            meeting = Meeting.objects.get(id=data["server_id"], mr=self.user)
            doctor_id = meeting.doctor_id
            soft_delete_instance(meeting, "updated_at")
            refresh_doctor_meetings_count(doctor_id)
            return {"server_id": str(meeting.id)}
        raise ValueError(f"Unknown action: {action}")

    def _handle_meeting_notes(self, action, data):
        # Slide notes carry a slide_id; general meeting notes do not.
        if data.get("slide_id"):
            return self._handle_meeting_slide_notes(action, data)
        return self._handle_meeting_general_notes(action, data)

    def _handle_meeting_general_notes(self, action, data):
        if action == "create":
            note = MeetingNote.objects.create(
                meeting_id=data["meeting_id"],
                title=data.get("title", ""),
                notes=data.get("notes", ""),
            )
            return {"server_id": str(note.id)}
        elif action == "update":
            note = MeetingNote.objects.get(id=data["server_id"])
            for field in ("title", "notes"):
                if field in data:
                    setattr(note, field, data[field])
            note.save()
            return {"server_id": str(note.id)}
        elif action == "delete":
            note = MeetingNote.objects.get(id=data["server_id"])
            note.is_deleted = True
            note.save(update_fields=["is_deleted", "updated_at"])
            return {"server_id": str(note.id)}
        raise ValueError(f"Unknown action: {action}")

    def _handle_meeting_slide_notes(self, action, data):
        if action == "create":
            note = MeetingSlideNote.objects.create(
                meeting_id=data["meeting_id"],
                slide_id=data["slide_id"],
                slide_title=data.get("slide_title", ""),
                slide_order=data.get("slide_order", 0),
                brochure_id=data.get("brochure_id", ""),
                brochure_title=data.get("brochure_title") or data.get("custom_title", ""),
                note_text=data.get("note_text", ""),
            )
            refresh_meeting_presentation_slides(note.meeting)
            return {"server_id": str(note.id)}
        elif action == "update":
            note = MeetingSlideNote.objects.get(id=data["server_id"])
            if "custom_title" in data and "brochure_title" not in data:
                note.brochure_title = data["custom_title"]
            for field in (
                "slide_title",
                "slide_order",
                "brochure_id",
                "brochure_title",
                "note_text",
            ):
                if field in data:
                    setattr(note, field, data[field])
            note.save()
            refresh_meeting_presentation_slides(note.meeting)
            return {"server_id": str(note.id)}
        elif action == "delete":
            note = MeetingSlideNote.objects.get(id=data["server_id"])
            note.is_deleted = True
            note.save(update_fields=["is_deleted", "updated_at"])
            refresh_meeting_presentation_slides(note.meeting)
            return {"server_id": str(note.id)}
        raise ValueError(f"Unknown action: {action}")

    def _handle_meeting_followups(self, action, data):
        if action == "create":
            followup = MeetingFollowUp.objects.create(
                meeting_id=data["meeting_id"],
                follow_up_date=data["follow_up_date"],
                follow_up_time=data.get("follow_up_time", ""),
                follow_up_notes=data.get("follow_up_notes", ""),
            )
            return {"server_id": str(followup.id)}
        elif action == "update":
            fu = MeetingFollowUp.objects.get(id=data["server_id"])
            for field in ("follow_up_date", "follow_up_time", "follow_up_notes", "status"):
                if field in data:
                    setattr(fu, field, data[field])
            fu.save()
            return {"server_id": str(fu.id)}
        elif action == "delete":
            fu = MeetingFollowUp.objects.get(id=data["server_id"])
            fu.is_deleted = True
            fu.save(update_fields=["is_deleted", "updated_at"])
            return {"server_id": str(fu.id)}
        raise ValueError(f"Unknown action: {action}")

    def _handle_saved_brochures(self, action, data):
        if action == "create":
            if "brochure_id" not in data:
                raise ValueError("brochure_id is required for saved_brochures create")
            if data.get("is_deleted"):
                if not data.get("server_id"):
                    raise ValueError("server_id is required to delete via sync")
                saved = soft_delete_saved_brochure(self.user, server_id=data["server_id"])
                return {"server_id": str(saved.id) if saved else data.get("server_id", "")}

            saved = create_saved_brochure(
                self.user,
                brochure_id=data["brochure_id"],
                brochure_title=data.get("brochure_title", ""),
                custom_title=data.get("custom_title", ""),
                original_brochure_data=data.get("original_brochure_data", {}),
            )
            return {"server_id": str(saved.id)}

        if not data.get("server_id"):
            raise ValueError("server_id is required for saved_brochures update/delete")

        if data.get("is_deleted") or action == "delete":
            saved = soft_delete_saved_brochure(self.user, server_id=data["server_id"])
            if not saved:
                raise ValueError("Saved brochure not found")
            return {"server_id": str(saved.id)}

        if action == "update":
            saved = update_saved_brochure(
                self.user,
                data["server_id"],
                custom_title=data.get("custom_title"),
                brochure_title=data.get("brochure_title"),
            )
            if not saved:
                raise ValueError("Saved brochure not found")
            return {"server_id": str(saved.id)}

        raise ValueError(f"Unknown action: {action}")

    def _handle_brochure_sync(self, action, data):
        brochure_id = str(data.get("brochureId") or data.get("brochure_id", ""))
        if not brochure_id:
            raise ValueError("brochure_id is required for brochure_sync")

        if action in ("create", "update"):
            brochure_title = (
                data.get("brochure_title")
                or data.get("title")
                or data.get("custom_title")
                or ""
            )
            # Prefer explicit brochure_data; do not wipe existing customizations if omitted.
            defaults = {
                "brochure_title": brochure_title,
                "is_deleted": False,
            }
            if "brochure_data" in data:
                defaults["brochure_data"] = data.get("brochure_data") or {}
            elif "slides" in data or "groups" in data:
                defaults["brochure_data"] = {
                    "slides": data.get("slides") or [],
                    "groups": data.get("groups") or data.get("slide_groups") or [],
                }

            sync, _ = BrochureSync.objects.update_or_create(
                mr=self.user,
                brochure_id=brochure_id,
                defaults=defaults,
            )
            return {"server_id": str(sync.id)}
        elif action == "delete":
            sync = BrochureSync.objects.filter(mr=self.user, brochure_id=brochure_id).first()
            if sync:
                soft_delete_instance(sync, "last_modified")
                return {"server_id": str(sync.id)}
            return {"server_id": ""}
        raise ValueError(f"Unknown action: {action}")

    def _handle_activity_logs(self, action, data):
        if action == "create":
            activity_type = (
                data.get("activity_type")
                or data.get("action")
                or data.get("type")
                or ""
            )
            log = log_activity(
                self.user,
                action=data.get("action", ""),
                activity_type=activity_type,
                entity_type=data.get("entity_type", ""),
                entity_id=data.get("entity_id") or data.get("server_id"),
                description=data.get("description", ""),
                details=data.get("details"),
                metadata=data.get("metadata") or data.get("details"),
            )
            return {"server_id": str(log.id)}
        raise ValueError(f"Unknown action: {action}")
