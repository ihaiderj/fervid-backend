from django.db.models import Count, Q
from django.utils import timezone

from accounts.models import User
from activity.models import ActivityLog
from brochures.models import Brochure
from doctors.models import Doctor, DoctorAssignment
from meetings.models import Meeting


def get_admin_dashboard_stats():
    now = timezone.now()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return {
        "total_mrs": User.objects.filter(role="mr", is_active=True).count(),
        "active_brochures": Brochure.objects.filter(
            status="active", is_deleted=False
        ).count(),
        "total_doctors": Doctor.objects.filter(is_deleted=False).count(),
        "monthly_meetings": Meeting.objects.filter(
            scheduled_date__gte=month_start, is_deleted=False
        ).count(),
    }


def get_mr_dashboard_stats(mr):
    now = timezone.now()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    meetings = Meeting.objects.filter(mr=mr, is_deleted=False)
    return {
        "active_presentations": meetings.filter(status="active").count(),
        "scheduled_meetings": meetings.filter(status="scheduled").count(),
        "doctors_connected": DoctorAssignment.objects.filter(
            mr=mr, status="active"
        ).count(),
        "monthly_meetings": meetings.filter(scheduled_date__gte=month_start).count(),
        "completed_meetings": meetings.filter(
            status="completed", scheduled_date__gte=month_start
        ).count(),
        "brochures_uploaded": Brochure.objects.filter(uploaded_by=mr).count(),
        "brochures_available": Brochure.objects.filter(
            status="active", is_public=True, is_deleted=False
        ).count(),
    }


def get_mr_performance_stats():
    mrs = User.objects.filter(role="mr").annotate(
        total_meetings=Count("meetings", filter=Q(meetings__is_deleted=False)),
        completed_meetings=Count(
            "meetings",
            filter=Q(meetings__status="completed", meetings__is_deleted=False),
        ),
        total_doctors=Count(
            "doctor_assignments",
            filter=Q(doctor_assignments__status="active"),
        ),
        brochures_uploaded=Count("uploaded_brochures"),
    )
    results = []
    for mr in mrs:
        last_log = (
            ActivityLog.objects.filter(user=mr).order_by("-created_at").first()
        )
        results.append(
            {
                "mr_id": str(mr.id),
                "mr_name": mr.full_name,
                "total_meetings": mr.total_meetings,
                "completed_meetings": mr.completed_meetings,
                "total_doctors": mr.total_doctors,
                "brochures_uploaded": mr.brochures_uploaded,
                "last_activity": last_log.created_at.isoformat() if last_log else None,
            }
        )
    return results


def get_brochure_analytics():
    brochures = Brochure.objects.filter(is_deleted=False).select_related("category_ref")
    return [
        {
            "brochure_id": str(b.id),
            "title": b.title,
            "category": b.category_name,
            "total_views": b.view_count,
            "total_downloads": b.download_count,
            "last_viewed": b.updated_at.isoformat() if b.view_count else None,
            "created_at": b.created_at.isoformat(),
        }
        for b in brochures
    ]


def get_system_status():
    total_users = User.objects.count()
    active_users = User.objects.filter(is_active=True).count()
    return {
        "server_status": "online",
        "database_status": "connected",
        "total_users": total_users,
        "active_users": active_users,
        "storage_used_mb": 0,
        "storage_percentage": 0,
        "last_backup": timezone.now().isoformat(),
        "uptime_hours": 24,
    }


def log_activity(user, action="", activity_type="", entity_type="", entity_id=None,
                 description="", details=None, metadata=None, request=None):
    ip = None
    ua = ""
    if request:
        ip = request.META.get("REMOTE_ADDR")
        ua = request.META.get("HTTP_USER_AGENT", "")
    return ActivityLog.objects.create(
        user=user,
        action=action,
        activity_type=activity_type or action,
        entity_type=entity_type,
        entity_id=entity_id,
        description=description,
        details=details or {},
        metadata=metadata or details or {},
        ip_address=ip,
        user_agent=ua,
    )
