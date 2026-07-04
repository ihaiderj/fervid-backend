from django.utils import timezone
from rest_framework.views import APIView

from accounts.models import UserSession
from accounts.serializers import SessionRegisterSerializer, UserSessionSerializer
from core.mixins import APIResponseMixin


class SessionRegisterView(APIResponseMixin, APIView):
    def post(self, request):
        serializer = SessionRegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        device_id = serializer.validated_data["device_id"]
        device_info = serializer.validated_data.get("device_info", "")

        deactivated = []
        other_sessions = UserSession.objects.filter(
            user=request.user, is_active=True
        ).exclude(device_id=device_id)
        for session in other_sessions:
            session.is_active = False
            session.ended_at = timezone.now()
            session.save(update_fields=["is_active", "ended_at"])
            deactivated.append(session.device_id)

        session, _ = UserSession.objects.update_or_create(
            user=request.user,
            device_id=device_id,
            defaults={
                "device_info": device_info,
                "is_active": True,
                "ended_at": None,
                "last_activity": timezone.now(),
            },
        )

        return self.success(
            {
                "session": UserSessionSerializer(session).data,
                "deactivated_devices": deactivated,
                "conflict": len(deactivated) > 0,
            }
        )
