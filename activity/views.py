from rest_framework.views import APIView

from activity.models import ActivityLog
from activity.serializers import ActivityLogSerializer, CreateActivityLogSerializer
from core.mixins import APIResponseMixin
from core.permissions import IsAdminOrMR
from core.services import log_activity


class ActivityLogView(APIResponseMixin, APIView):
    permission_classes = [IsAdminOrMR]

    def post(self, request):
        serializer = CreateActivityLogSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        user = request.user
        if data.get("user_id") and request.user.role == "admin":
            from accounts.models import User
            user = User.objects.filter(id=data["user_id"]).first() or user

        log = log_activity(
            user,
            action=data.get("action", ""),
            activity_type=data.get("activity_type", data.get("action", "")),
            entity_type=data.get("entity_type", ""),
            entity_id=data.get("entity_id"),
            description=data.get("description", ""),
            details=data.get("details"),
            metadata=data.get("metadata"),
            request=request,
        )
        return self.success(ActivityLogSerializer(log).data, status_code=201)

    def get(self, request):
        qs = ActivityLog.objects.select_related("user").order_by("-created_at")
        if request.user.role != "admin":
            qs = qs.filter(user=request.user)
        limit = int(request.query_params.get("limit", 50))
        return self.success(ActivityLogSerializer(qs[:limit], many=True).data)
