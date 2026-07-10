from django.db import transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.views import APIView

from brochures.storage import save_uploaded_file
from brochures.models import Brochure, BrochureSync, SavedBrochure
from brochures.saved_brochure_service import (
    get_saved_brochure_for_mr,
    soft_delete_saved_brochure,
    upsert_saved_brochure,
)
from core.soft_delete import soft_delete_instance
from brochures.serializers import (
    BrochureSyncSerializer,
    CreateBrochureSerializer,
    MRAssignedBrochureSerializer,
    SavedBrochureSerializer,
)
from core.mixins import APIResponseMixin
from core.permissions import CanManageDoctors, CanUploadBrochures, IsMR
from core.services import get_mr_dashboard_stats, log_activity
from doctors.models import Doctor, DoctorAssignment
from doctors.serializers import CreateDoctorSerializer, MRAssignedDoctorSerializer
from meetings.models import Meeting, MeetingFollowUp, MeetingSlideNote
from meetings.serializers import (
    AddSlideNoteSerializer,
    CreateFollowUpSerializer,
    CreateMeetingSerializer,
    LegacyFollowUpSerializer,
    MRMeetingSerializer,
    MRUpcomingMeetingSerializer,
    MeetingFollowUpSerializer,
    SlideNoteSerializer,
    UpdateMeetingSerializer,
)


class MRDashboardStatsView(APIResponseMixin, APIView):
    permission_classes = [IsMR]

    def get(self, request):
        return self.success(get_mr_dashboard_stats(request.user))


class MRRecentActivitiesView(APIResponseMixin, APIView):
    permission_classes = [IsMR]

    def get(self, request):
        from activity.models import ActivityLog

        limit = int(request.query_params.get("limit", 10))
        logs = ActivityLog.objects.filter(user=request.user).order_by("-created_at")[:limit]
        data = [
            {
                "id": str(log.id),
                "activity_type": log.activity_type or log.action,
                "description": log.description,
                "created_at": log.created_at.isoformat(),
            }
            for log in logs
        ]
        return self.success(data)


class MRPerformanceSummaryView(APIResponseMixin, APIView):
    permission_classes = [IsMR]

    def get(self, request):
        stats = get_mr_dashboard_stats(request.user)
        total = stats["monthly_meetings"]
        completed = stats["completed_meetings"]
        rate = round((completed / total * 100) if total else 0, 1)
        return self.success(
            {
                "total_meetings_this_month": total,
                "completed_meetings_this_month": completed,
                "total_doctors_assigned": stats["doctors_connected"],
                "brochures_uploaded_this_month": stats["brochures_uploaded"],
                "completion_rate": rate,
            }
        )


class MRBrochureListView(APIResponseMixin, APIView):
    permission_classes = [IsMR]

    def get(self, request):
        brochures = Brochure.objects.filter(
            status="active", is_public=True, is_deleted=False
        ).select_related("uploaded_by", "assigned_by", "category_ref")
        return self.success(MRAssignedBrochureSerializer(brochures, many=True).data)


class MRBrochureUploadView(APIResponseMixin, APIView):
    permission_classes = [CanUploadBrochures]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        from brochures.models import BrochureCategory
        from brochures.serializers import BrochureSerializer

        serializer = CreateBrochureSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        category_ref = None
        category_name = data.get("category", "")
        if data.get("category_id"):
            category_ref = BrochureCategory.objects.filter(id=data["category_id"]).first()
            if category_ref:
                category_name = category_ref.name

        file_url = data.get("file_url", "")
        if "file" in request.FILES:
            file_url = save_uploaded_file(request.FILES["file"], "brochures")

        brochure = Brochure.objects.create(
            title=data["title"],
            category=category_name,
            category_ref=category_ref,
            description=data.get("description", ""),
            file_url=file_url,
            uploaded_by=request.user,
            is_public=data.get("is_public", True),
        )
        return self.success(
            BrochureSerializer(brochure).data, status_code=status.HTTP_201_CREATED
        )


class MRPresentationsView(APIResponseMixin, APIView):
    permission_classes = [IsMR]

    def get(self, request):
        brochures = Brochure.objects.filter(
            uploaded_by=request.user, is_deleted=False
        )
        data = [
            {
                "presentation_id": str(b.id),
                "title": b.title,
                "category": b.category_name,
                "description": b.description,
                "thumbnail_url": b.thumbnail_url,
                "total_slides": b.pages or 0,
                "times_used": b.view_count,
                "last_used_date": b.updated_at.isoformat(),
                "view_count": b.view_count,
                "download_count": b.download_count,
                "created_at": b.created_at.isoformat(),
            }
            for b in brochures
        ]
        return self.success(data)


class MRDoctorListView(APIResponseMixin, APIView):
    permission_classes = [IsMR]

    def get(self, request):
        doctor_ids = DoctorAssignment.objects.filter(
            mr=request.user, status="active"
        ).values_list("doctor_id", flat=True)
        doctors = Doctor.objects.filter(id__in=doctor_ids, is_deleted=False)
        return self.success(MRAssignedDoctorSerializer(doctors, many=True).data)


class MRDoctorAssignmentView(APIResponseMixin, APIView):
    permission_classes = [CanManageDoctors]

    def post(self, request):
        serializer = CreateDoctorSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            doctor = serializer.save(created_by=request.user)
            DoctorAssignment.objects.create(
                doctor=doctor,
                mr=request.user,
                assigned_by=request.user,
                status="active",
            )
        return self.success(
            MRAssignedDoctorSerializer(doctor).data, status_code=status.HTTP_201_CREATED
        )

    def patch(self, request, pk):
        try:
            doctor = Doctor.objects.get(id=pk, is_deleted=False)
        except Doctor.DoesNotExist:
            return self.error("Doctor not found", code="NOT_FOUND", status_code=404)

        if not DoctorAssignment.objects.filter(
            doctor=doctor, mr=request.user, status="active"
        ).exists():
            return self.error("Not assigned to this doctor", code="FORBIDDEN", status_code=403)

        serializer = CreateDoctorSerializer(doctor, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return self.success(MRAssignedDoctorSerializer(doctor).data)

    def delete(self, request, pk):
        assignment = DoctorAssignment.objects.filter(
            doctor_id=pk, mr=request.user, status="active"
        ).first()
        if not assignment:
            return self.error("Assignment not found", code="NOT_FOUND", status_code=404)
        assignment.status = "inactive"
        assignment.save(update_fields=["status"])
        return self.success(message="Assignment removed")


class MRMeetingListView(APIResponseMixin, APIView):
    permission_classes = [IsMR]

    def get(self, request):
        meetings = (
            Meeting.objects.filter(mr=request.user, is_deleted=False)
            .select_related("doctor", "brochure")
            .prefetch_related("slide_notes")
        )
        return self.success(MRMeetingSerializer(meetings, many=True).data)

    def post(self, request):
        serializer = CreateMeetingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        if not DoctorAssignment.objects.filter(
            doctor_id=data["doctor_id"], mr=request.user, status="active"
        ).exists():
            return self.error(
                "Doctor not assigned to you", code="NOT_ASSIGNED", status_code=403
            )

        brochure = None
        if data.get("brochure_id"):
            brochure = Brochure.objects.filter(id=data["brochure_id"]).first()

        meeting = Meeting.objects.create(
            mr=request.user,
            doctor_id=data["doctor_id"],
            brochure=brochure,
            title=data["title"],
            purpose=data.get("purpose", ""),
            scheduled_date=data.get("scheduled_date") or timezone.now(),
            duration_minutes=data.get("duration_minutes", 30),
            location=data.get("location", ""),
            notes=data.get("notes", ""),
            presentation_slides={
                "brochure_id": str(data.get("brochure_id", "")),
                "brochure_title": data.get("brochure_title", ""),
            },
        )
        return self.success(
            {"meeting_id": str(meeting.id)}, status_code=status.HTTP_201_CREATED
        )


class MRUpcomingMeetingsView(APIResponseMixin, APIView):
    permission_classes = [IsMR]

    def get(self, request):
        limit = int(request.query_params.get("limit", 5))
        meetings = (
            Meeting.objects.filter(
                mr=request.user,
                is_deleted=False,
                status="scheduled",
                scheduled_date__gte=timezone.now(),
            )
            .select_related("doctor")
            .order_by("scheduled_date")[:limit]
        )
        return self.success(MRUpcomingMeetingSerializer(meetings, many=True).data)


class MRMeetingDetailView(APIResponseMixin, APIView):
    permission_classes = [IsMR]

    def get(self, request, pk):
        try:
            meeting = Meeting.objects.select_related("doctor", "brochure").get(
                id=pk, mr=request.user, is_deleted=False
            )
        except Meeting.DoesNotExist:
            return self.error("Meeting not found", code="NOT_FOUND", status_code=404)

        notes = meeting.slide_notes.filter(is_deleted=False)
        return self.success(
            {
                "meeting": MRMeetingSerializer(meeting).data,
                "slide_notes": SlideNoteSerializer(notes, many=True).data,
            }
        )

    def patch(self, request, pk):
        try:
            meeting = Meeting.objects.get(id=pk, mr=request.user, is_deleted=False)
        except Meeting.DoesNotExist:
            return self.error("Meeting not found", code="NOT_FOUND", status_code=404)

        serializer = UpdateMeetingSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        for field, value in serializer.validated_data.items():
            setattr(meeting, field, value)
        meeting.save()
        return self.success(MRMeetingSerializer(meeting).data)

    def delete(self, request, pk):
        try:
            meeting = Meeting.objects.get(id=pk, mr=request.user)
        except Meeting.DoesNotExist:
            return self.error("Meeting not found", code="NOT_FOUND", status_code=404)
        meeting.is_deleted = True
        meeting.save(update_fields=["is_deleted", "updated_at"])
        return self.success(message="Meeting deleted")


class MRMeetingNotesView(APIResponseMixin, APIView):
    permission_classes = [IsMR]

    def post(self, request, pk):
        try:
            meeting = Meeting.objects.get(id=pk, mr=request.user, is_deleted=False)
        except Meeting.DoesNotExist:
            return self.error("Meeting not found", code="NOT_FOUND", status_code=404)

        serializer = AddSlideNoteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        note = MeetingSlideNote.objects.create(meeting=meeting, **data)
        return self.success(
            SlideNoteSerializer(note).data, status_code=status.HTTP_201_CREATED
        )


class MRMeetingNoteDetailView(APIResponseMixin, APIView):
    permission_classes = [IsMR]

    def patch(self, request, pk, note_id):
        note = MeetingSlideNote.objects.filter(
            id=note_id, meeting_id=pk, meeting__mr=request.user, is_deleted=False
        ).first()
        if not note:
            return self.error("Note not found", code="NOT_FOUND", status_code=404)
        note.note_text = request.data.get("note_text", note.note_text)
        note.save()
        return self.success(SlideNoteSerializer(note).data)

    def delete(self, request, pk, note_id):
        note = MeetingSlideNote.objects.filter(
            id=note_id, meeting_id=pk, meeting__mr=request.user
        ).first()
        if not note:
            return self.error("Note not found", code="NOT_FOUND", status_code=404)
        note.is_deleted = True
        note.save(update_fields=["is_deleted", "updated_at"])
        return self.success(message="Note deleted")


class MRMeetingFollowUpListView(APIResponseMixin, APIView):
    permission_classes = [IsMR]

    def get(self, request, pk):
        followups = MeetingFollowUp.objects.filter(
            meeting_id=pk, meeting__mr=request.user, is_deleted=False
        )
        return self.success(MeetingFollowUpSerializer(followups, many=True).data)

    def post(self, request, pk):
        try:
            meeting = Meeting.objects.get(id=pk, mr=request.user, is_deleted=False)
        except Meeting.DoesNotExist:
            return self.error("Meeting not found", code="NOT_FOUND", status_code=404)

        serializer = CreateFollowUpSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        seq = meeting.followups.filter(is_deleted=False).count() + 1
        followup = MeetingFollowUp.objects.create(
            meeting=meeting,
            sequence_number=seq,
            **data,
        )
        return self.success(
            {"follow_up_id": str(followup.id)},
            status_code=status.HTTP_201_CREATED,
        )


class MRLegacyFollowUpView(APIResponseMixin, APIView):
    permission_classes = [IsMR]

    def patch(self, request, pk):
        try:
            meeting = Meeting.objects.get(id=pk, mr=request.user, is_deleted=False)
        except Meeting.DoesNotExist:
            return self.error("Meeting not found", code="NOT_FOUND", status_code=404)

        serializer = LegacyFollowUpSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        for field, value in serializer.validated_data.items():
            setattr(meeting, field, value)
        meeting.save()
        return self.success(MRMeetingSerializer(meeting).data)


class MRFollowUpDetailView(APIResponseMixin, APIView):
    permission_classes = [IsMR]

    def patch(self, request, pk):
        followup = MeetingFollowUp.objects.filter(
            id=pk, meeting__mr=request.user, is_deleted=False
        ).first()
        if not followup:
            return self.error("Follow-up not found", code="NOT_FOUND", status_code=404)

        for field in ("follow_up_date", "follow_up_time", "follow_up_notes", "status"):
            if field in request.data:
                setattr(followup, field, request.data[field])
        followup.save()
        return self.success(MeetingFollowUpSerializer(followup).data)

    def delete(self, request, pk):
        followup = MeetingFollowUp.objects.filter(id=pk, meeting__mr=request.user).first()
        if not followup:
            return self.error("Follow-up not found", code="NOT_FOUND", status_code=404)
        followup.is_deleted = True
        followup.save(update_fields=["is_deleted", "updated_at"])
        return self.success(message="Follow-up deleted")


class MRSavedBrochureView(APIResponseMixin, APIView):
    permission_classes = [IsMR]

    def get(self, request):
        saved = SavedBrochure.objects.filter(mr=request.user, is_deleted=False)
        return self.success(SavedBrochureSerializer(saved, many=True).data)

    def post(self, request):
        brochure_id = request.data.get("brochure_id") or request.data.get("p_brochure_id")
        if not brochure_id:
            return self.error("brochure_id is required", code="MISSING_BROCHURE_ID")

        saved, created = upsert_saved_brochure(
            request.user,
            brochure_id=brochure_id,
            brochure_title=request.data.get("brochure_title", ""),
            custom_title=request.data.get("custom_title", ""),
            original_brochure_data=request.data.get("original_brochure_data", {}),
        )
        return self.success(
            SavedBrochureSerializer(saved).data,
            status_code=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class MRSavedBrochureDetailView(APIResponseMixin, APIView):
    permission_classes = [IsMR]

    def patch(self, request, pk):
        saved = get_saved_brochure_for_mr(request.user, pk)
        if not saved:
            return self.error("Not found", code="NOT_FOUND", status_code=404)
        saved.custom_title = request.data.get("custom_title", saved.custom_title)
        saved.save()
        return self.success(SavedBrochureSerializer(saved).data)

    def delete(self, request, pk):
        saved = soft_delete_saved_brochure(request.user, server_id=pk, brochure_id=pk)
        if not saved:
            return self.error("Not found", code="NOT_FOUND", status_code=404)
        return self.success(message="Removed")


class MRBrochureSyncView(APIResponseMixin, APIView):
    permission_classes = [IsMR]

    def get(self, request):
        syncs = BrochureSync.objects.filter(mr=request.user, is_deleted=False)
        return self.success(BrochureSyncSerializer(syncs, many=True).data)

    def put(self, request):
        brochure_id = str(
            request.data.get("brochure_id") or request.data.get("p_brochure_id", "")
        )
        sync, _ = BrochureSync.objects.update_or_create(
            mr=request.user,
            brochure_id=brochure_id,
            defaults={
                "brochure_title": request.data.get("brochure_title", ""),
                "brochure_data": request.data.get("brochure_data", {}),
                "is_deleted": False,
            },
        )
        return self.success(BrochureSyncSerializer(sync).data)


class MRBrochureSyncDetailView(APIResponseMixin, APIView):
    permission_classes = [IsMR]

    def delete(self, request, brochure_id):
        sync = BrochureSync.objects.filter(
            mr=request.user, brochure_id=brochure_id
        ).first()
        if sync:
            soft_delete_instance(sync, "last_modified")
        return self.success(message="Sync data deleted")
