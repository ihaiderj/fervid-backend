from django.utils import timezone
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.views import APIView

from accounts.models import MRPermission, User
from accounts.serializers import (
    CreateMRSerializer,
    MRDataSerializer,
    UpdateMRPermissionsSerializer,
    UpdateMRProfileSerializer,
)
from activity.models import ActivityLog
from activity.serializers import ActivityLogSerializer
from brochures.models import Brochure, BrochureCategory
from brochures.serializers import BrochureSerializer, CreateBrochureSerializer
from core.mixins import APIResponseMixin
from core.permissions import IsAdmin
from core.services import (
    get_admin_dashboard_stats,
    get_brochure_analytics,
    get_mr_performance_stats,
    get_system_status,
    log_activity,
)
from doctors.models import Doctor, DoctorAssignment
from doctors.serializers import AssignDoctorSerializer, CreateDoctorSerializer, DoctorSerializer
from meetings.models import Meeting
from meetings.serializers import MeetingSerializer


class AdminDashboardStatsView(APIResponseMixin, APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        return self.success(get_admin_dashboard_stats())


class AdminRecentActivitiesView(APIResponseMixin, APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        limit = int(request.query_params.get("limit", 10))
        logs = ActivityLog.objects.select_related("user").order_by("-created_at")[:limit]
        data = [
            {
                "id": str(log.id),
                "activity_type": log.activity_type or log.action,
                "description": log.description or str(log.details),
                "user_name": log.user.full_name if log.user else "System",
                "created_at": log.created_at.isoformat(),
            }
            for log in logs
        ]
        return self.success(data)


class AdminSystemStatusView(APIResponseMixin, APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        return self.success(get_system_status())


class AdminMRPerformanceView(APIResponseMixin, APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        return self.success(get_mr_performance_stats())


class AdminBrochureAnalyticsView(APIResponseMixin, APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        return self.success(get_brochure_analytics())


class AdminMRListView(APIResponseMixin, APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        include_permissions = request.query_params.get("include_permissions") == "true"
        mrs = User.objects.filter(role="mr")
        if include_permissions:
            mrs = mrs.prefetch_related("mr_permissions")
        data = []
        for mr in mrs:
            item = MRDataSerializer(mr).data
            item["doctors_count"] = DoctorAssignment.objects.filter(
                mr=mr, status="active"
            ).count()
            item["meetings_count"] = Meeting.objects.filter(mr=mr, is_deleted=False).count()
            if include_permissions:
                item["permissions"] = list(
                    mr.mr_permissions.values(
                        "permission_type", "is_granted", "expires_at"
                    )
                )
            data.append(item)
        return self.success(data)

    def post(self, request):
        serializer = CreateMRSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        if User.objects.filter(email=data["email"]).exists():
            return self.error("Email already exists", code="EMAIL_EXISTS")

        mr = User.objects.create_user(
            email=data["email"],
            password=data["password"],
            role="mr",
            first_name=data["first_name"],
            last_name=data["last_name"],
            phone=data.get("phone", ""),
            address=data.get("address", ""),
            profile_image_url=data.get("profile_image_url", ""),
            can_upload_brochures=data.get("can_upload_brochures", False),
            can_manage_doctors=data.get("can_manage_doctors", False),
            can_schedule_meetings=data.get("can_schedule_meetings", True),
        )

        for perm_type, granted in [
            ("upload_brochures", mr.can_upload_brochures),
            ("manage_doctors", mr.can_manage_doctors),
            ("schedule_meetings", mr.can_schedule_meetings),
        ]:
            MRPermission.objects.create(
                mr=mr,
                permission_type=perm_type,
                is_granted=granted,
                granted_by=request.user,
            )

        log_activity(
            request.user,
            action="create_mr",
            entity_type="user",
            entity_id=mr.id,
            description=f"Created MR {mr.email}",
            request=request,
        )
        return self.success(MRDataSerializer(mr).data, status_code=status.HTTP_201_CREATED)


class AdminMRDetailView(APIResponseMixin, APIView):
    permission_classes = [IsAdmin]

    def patch(self, request, pk):
        try:
            mr = User.objects.get(id=pk, role="mr")
        except User.DoesNotExist:
            return self.error("MR not found", code="NOT_FOUND", status_code=404)

        serializer = UpdateMRProfileSerializer(mr, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return self.success(MRDataSerializer(mr).data)

    def delete(self, request, pk):
        try:
            mr = User.objects.get(id=pk, role="mr")
        except User.DoesNotExist:
            return self.error("MR not found", code="NOT_FOUND", status_code=404)

        mr.delete()
        log_activity(
            request.user,
            action="hard_delete_mr",
            entity_type="user",
            entity_id=pk,
            request=request,
        )
        return self.success(message="MR permanently deleted")


class AdminMRPermissionsView(APIResponseMixin, APIView):
    permission_classes = [IsAdmin]

    def patch(self, request, pk):
        try:
            mr = User.objects.get(id=pk, role="mr")
        except User.DoesNotExist:
            return self.error("MR not found", code="NOT_FOUND", status_code=404)

        serializer = UpdateMRPermissionsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        for field, value in serializer.validated_data.items():
            setattr(mr, field, value)
        mr.save()

        perm_map = {
            "can_upload_brochures": "upload_brochures",
            "can_manage_doctors": "manage_doctors",
            "can_schedule_meetings": "schedule_meetings",
        }
        for field, perm_type in perm_map.items():
            if field in serializer.validated_data:
                MRPermission.objects.update_or_create(
                    mr=mr,
                    permission_type=perm_type,
                    defaults={
                        "is_granted": serializer.validated_data[field],
                        "granted_by": request.user,
                    },
                )
        return self.success(MRDataSerializer(mr).data)


class AdminMRDeactivateView(APIResponseMixin, APIView):
    permission_classes = [IsAdmin]

    def post(self, request, pk):
        try:
            mr = User.objects.get(id=pk, role="mr")
        except User.DoesNotExist:
            return self.error("MR not found", code="NOT_FOUND", status_code=404)

        mr.is_active = False
        mr.save(update_fields=["is_active"])
        return self.success(message="MR deactivated")


class AdminBrochureListView(APIResponseMixin, APIView):
    permission_classes = [IsAdmin]
    parser_classes = [MultiPartParser, FormParser]

    def get(self, request):
        with_categories = request.query_params.get("with_categories") == "true"
        brochures = Brochure.objects.filter(is_deleted=False).select_related(
            "category_ref", "assigned_by", "uploaded_by"
        )
        data = BrochureSerializer(brochures, many=True).data
        if with_categories:
            categories = list(
                BrochureCategory.objects.filter(is_active=True).values(
                    "id", "name", "color"
                )
            )
            return self.success({"brochures": data, "categories": categories})
        return self.success(data)

    def post(self, request):
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
            uploaded = request.FILES["file"]
            file_url = save_uploaded_file(uploaded, "brochures")

        brochure = Brochure.objects.create(
            title=data["title"],
            category=category_name,
            category_ref=category_ref,
            description=data.get("description", ""),
            file_url=file_url,
            file_name=data.get("file_name") or (uploaded.name if "file" in request.FILES else ""),
            file_type=data.get("file_type", ""),
            pages=data.get("pages"),
            file_size=data.get("file_size", ""),
            thumbnail_url=data.get("thumbnail_url", ""),
            tags=data.get("tags", []),
            is_public=data.get("is_public", True),
            uploaded_by=request.user,
            assigned_by=request.user,
        )
        return self.success(
            BrochureSerializer(brochure).data, status_code=status.HTTP_201_CREATED
        )


class AdminBrochureCategoryListView(APIResponseMixin, APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        categories = BrochureCategory.objects.filter(is_active=True)
        return self.success(
            list(categories.values("id", "name", "description", "color"))
        )


class AdminDoctorListView(APIResponseMixin, APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        doctors = Doctor.objects.filter(is_deleted=False).prefetch_related("assignments__mr")
        return self.success(DoctorSerializer(doctors, many=True).data)

    def post(self, request):
        serializer = CreateDoctorSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        doctor = serializer.save(created_by=request.user)
        return self.success(
            DoctorSerializer(doctor).data, status_code=status.HTTP_201_CREATED
        )


class AdminDoctorAssignmentView(APIResponseMixin, APIView):
    permission_classes = [IsAdmin]

    def post(self, request):
        serializer = AssignDoctorSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        assignment, created = DoctorAssignment.objects.get_or_create(
            doctor_id=data["doctor_id"],
            mr_id=data["mr_id"],
            status="active",
            defaults={
                "assigned_by": request.user,
                "notes": data.get("notes", ""),
            },
        )
        if not created:
            return self.error("Assignment already exists", code="DUPLICATE")
        return self.success(
            {"id": str(assignment.id)}, status_code=status.HTTP_201_CREATED
        )


class AdminMeetingListView(APIResponseMixin, APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        meetings = Meeting.objects.filter(is_deleted=False).select_related(
            "mr", "doctor", "brochure"
        )
        return self.success(MeetingSerializer(meetings, many=True).data)


from brochures.storage import save_uploaded_file
