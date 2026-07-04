from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework.views import APIView

from activity.models import ActivityLog
from activity.serializers import CreateActivityLogSerializer
from core.mixins import APIResponseMixin
from core.services import log_activity
from sync.handlers import SyncPushHandler


class SyncPushView(APIResponseMixin, APIView):
    def post(self, request):
        operations = request.data.get("operations", [])
        handler = SyncPushHandler(request.user)
        results = handler.process(operations)
        return self.success({"results": results})


class SyncPullView(APIResponseMixin, APIView):
    def get(self, request):
        since_str = request.query_params.get("since")
        since = parse_datetime(since_str) if since_str else None
        user = request.user

        from doctors.models import Doctor, DoctorAssignment
        from brochures.models import BrochureSync, SavedBrochure
        from meetings.models import Meeting, MeetingFollowUp, MeetingSlideNote

        def changed_qs(qs, since):
            if since:
                return qs.filter(updated_at__gte=since)
            return qs

        doctor_ids = DoctorAssignment.objects.filter(
            mr=user, status="active"
        ).values_list("doctor_id", flat=True)

        data = {
            "doctors": list(
                changed_qs(Doctor.objects.filter(id__in=doctor_ids), since).values()
            ),
            "meetings": list(
                changed_qs(Meeting.objects.filter(mr=user), since).values()
            ),
            "meeting_slide_notes": list(
                changed_qs(
                    MeetingSlideNote.objects.filter(meeting__mr=user), since
                ).values()
            ),
            "meeting_followups": list(
                changed_qs(
                    MeetingFollowUp.objects.filter(meeting__mr=user), since
                ).values()
            ),
            "saved_brochures": list(
                changed_qs(SavedBrochure.objects.filter(mr=user), since).values()
            ),
            "brochure_sync": list(
                changed_qs(BrochureSync.objects.filter(mr=user), since).values()
            ),
            "activity_logs": list(
                (
                    ActivityLog.objects.filter(user=user, created_at__gte=since)
                    if since
                    else ActivityLog.objects.filter(user=user)
                ).values()
            ),
            "sync_timestamp": timezone.now().isoformat(),
        }
        return self.success(data)


class SyncStatusView(APIResponseMixin, APIView):
    def get(self, request):
        return self.success(
            {
                "status": "ok",
                "server_time": timezone.now().isoformat(),
                "user_id": str(request.user.id),
            }
        )
