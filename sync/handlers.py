from django.utils import timezone

from activity.models import ActivityLog
from brochures.models import BrochureSync, SavedBrochure
from brochures.saved_brochure_service import (
    get_saved_brochure_for_mr,
    soft_delete_saved_brochure,
    upsert_saved_brochure,
)
from core.soft_delete import soft_delete_instance
from core.services import log_activity
from doctors.models import Doctor, DoctorAssignment
from meetings.models import Meeting, MeetingFollowUp, MeetingSlideNote


class SyncPushHandler:
    """Process offline sync queue operations from mobile client."""

    ENTITY_ORDER = [
        "doctors",
        "meetings",
        "meeting_notes",
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
        if action == "create":
            doctor = Doctor.objects.create(
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
            DoctorAssignment.objects.create(
                doctor=doctor, mr=self.user, assigned_by=self.user, status="active"
            )
            return {"server_id": str(doctor.id)}
        elif action == "update":
            doctor = Doctor.objects.get(id=data["server_id"])
            for field in ("first_name", "last_name", "specialty", "hospital", "phone", "email", "location", "notes"):
                if field in data:
                    setattr(doctor, field, data[field])
            doctor.save()
            return {"server_id": str(doctor.id)}
        elif action == "delete":
            doctor = Doctor.objects.get(id=data["server_id"])
            doctor.is_deleted = True
            doctor.save(update_fields=["is_deleted", "updated_at"])
            return {"server_id": str(doctor.id)}
        raise ValueError(f"Unknown action: {action}")

    def _handle_meetings(self, action, data):
        if action == "create":
            meeting = Meeting.objects.create(
                mr=self.user,
                doctor_id=data["doctor_id"],
                title=data.get("title", "Meeting"),
                purpose=data.get("purpose", ""),
                scheduled_date=data.get("scheduled_date", timezone.now()),
                duration_minutes=data.get("duration_minutes", 30),
                presentation_slides={
                    "brochure_id": data.get("brochure_id", ""),
                    "brochure_title": data.get("brochure_title", ""),
                },
            )
            return {"server_id": str(meeting.id)}
        elif action == "update":
            meeting = Meeting.objects.get(id=data["server_id"], mr=self.user)
            for field in ("title", "status", "location", "notes", "scheduled_date", "duration_minutes"):
                if field in data:
                    setattr(meeting, field, data[field])
            meeting.save()
            return {"server_id": str(meeting.id)}
        elif action == "delete":
            meeting = Meeting.objects.get(id=data["server_id"], mr=self.user)
            meeting.is_deleted = True
            meeting.save(update_fields=["is_deleted", "updated_at"])
            return {"server_id": str(meeting.id)}
        raise ValueError(f"Unknown action: {action}")

    def _handle_meeting_notes(self, action, data):
        return self._handle_meeting_slide_notes(action, data)

    def _handle_meeting_slide_notes(self, action, data):
        if action == "create":
            note = MeetingSlideNote.objects.create(
                meeting_id=data["meeting_id"],
                slide_id=data["slide_id"],
                note_text=data.get("note_text", ""),
            )
            return {"server_id": str(note.id)}
        elif action == "update":
            note = MeetingSlideNote.objects.get(id=data["server_id"])
            note.note_text = data.get("note_text", note.note_text)
            note.save()
            return {"server_id": str(note.id)}
        elif action == "delete":
            note = MeetingSlideNote.objects.get(id=data["server_id"])
            note.is_deleted = True
            note.save(update_fields=["is_deleted", "updated_at"])
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
        if "brochure_id" not in data and not data.get("server_id"):
            raise ValueError("brochure_id or server_id is required for saved_brochures sync")

        if data.get("is_deleted"):
            saved = soft_delete_saved_brochure(
                self.user,
                brochure_id=data.get("brochure_id"),
                server_id=data.get("server_id"),
            )
            return {"server_id": str(saved.id) if saved else data.get("server_id", "")}

        if action == "create":
            if "brochure_id" not in data:
                raise ValueError("brochure_id is required for saved_brochures create")
            saved, _ = upsert_saved_brochure(
                self.user,
                brochure_id=data["brochure_id"],
                brochure_title=data.get("brochure_title", ""),
                custom_title=data.get("custom_title", ""),
                original_brochure_data=data.get("original_brochure_data", {}),
            )
            return {"server_id": str(saved.id)}
        elif action == "update":
            saved = get_saved_brochure_for_mr(
                self.user, data.get("server_id") or data.get("brochure_id")
            )
            if not saved:
                raise ValueError("Saved brochure not found")
            if "custom_title" in data:
                saved.custom_title = data["custom_title"]
            if data.get("brochure_title"):
                saved.brochure_title = data["brochure_title"]
            if data.get("original_brochure_data"):
                saved.original_brochure_data = data["original_brochure_data"]
            saved.is_deleted = False
            saved.save()
            return {"server_id": str(saved.id)}
        elif action == "delete":
            saved = soft_delete_saved_brochure(
                self.user,
                brochure_id=data.get("brochure_id"),
                server_id=data.get("server_id"),
            )
            if not saved:
                raise ValueError("Saved brochure not found")
            return {"server_id": str(saved.id)}
        raise ValueError(f"Unknown action: {action}")

    def _handle_brochure_sync(self, action, data):
        brochure_id = str(data.get("brochureId") or data.get("brochure_id", ""))
        if action in ("create", "update"):
            sync, _ = BrochureSync.objects.update_or_create(
                mr=self.user,
                brochure_id=brochure_id,
                defaults={
                    "brochure_title": data.get("title", ""),
                    "brochure_data": data.get("brochure_data", data),
                    "is_deleted": False,
                },
            )
            return {"server_id": str(sync.id)}
        elif action == "delete":
            sync = BrochureSync.objects.filter(mr=self.user, brochure_id=brochure_id).first()
            if sync:
                soft_delete_instance(sync, "last_modified")
                return {"server_id": str(sync.id)}
        raise ValueError(f"Unknown action: {action}")

    def _handle_activity_logs(self, action, data):
        if action == "create":
            log = log_activity(
                self.user,
                activity_type=data.get("activity_type", ""),
                description=data.get("description", ""),
                metadata=data.get("metadata"),
            )
            return {"server_id": str(log.id)}
        raise ValueError(f"Unknown action: {action}")
