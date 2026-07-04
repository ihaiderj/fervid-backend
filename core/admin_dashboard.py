from django.contrib import admin
from django.template.response import TemplateResponse

from activity.models import ActivityLog
from core.services import get_admin_dashboard_stats


def fervid_admin_index(request, extra_context=None):
    stats = get_admin_dashboard_stats()
    recent = ActivityLog.objects.select_related("user").order_by("-created_at")[:10]
    recent_activities = [
        {
            "created_at": log.created_at,
            "user_name": log.user.full_name if log.user else "System",
            "activity_type": log.activity_type or log.action,
            "description": log.description,
        }
        for log in recent
    ]
    context = {
        **admin.site.each_context(request),
        "title": admin.site.index_title,
        "subtitle": None,
        "app_list": admin.site.get_app_list(request),
        **stats,
        "recent_activities": recent_activities,
        **(extra_context or {}),
    }
    return TemplateResponse(request, "admin/index.html", context)

admin.site.index = fervid_admin_index
