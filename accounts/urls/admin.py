from django.urls import path

from accounts.views.admin_views import (
    AdminBrochureAnalyticsView,
    AdminBrochureCategoryListView,
    AdminBrochureListView,
    AdminDashboardStatsView,
    AdminDoctorAssignmentView,
    AdminDoctorListView,
    AdminMRDeactivateView,
    AdminMRDetailView,
    AdminMRListView,
    AdminMRPerformanceView,
    AdminMRPermissionsView,
    AdminMeetingListView,
    AdminRecentActivitiesView,
    AdminSystemStatusView,
)

urlpatterns = [
    path("dashboard/stats/", AdminDashboardStatsView.as_view()),
    path("dashboard/activities/", AdminRecentActivitiesView.as_view()),
    path("system/status/", AdminSystemStatusView.as_view()),
    path("analytics/mr-performance/", AdminMRPerformanceView.as_view()),
    path("analytics/brochures/", AdminBrochureAnalyticsView.as_view()),
    path("mrs/", AdminMRListView.as_view()),
    path("mrs/<uuid:pk>/", AdminMRDetailView.as_view()),
    path("mrs/<uuid:pk>/permissions/", AdminMRPermissionsView.as_view()),
    path("mrs/<uuid:pk>/deactivate/", AdminMRDeactivateView.as_view()),
    path("brochures/", AdminBrochureListView.as_view()),
    path("brochure-categories/", AdminBrochureCategoryListView.as_view()),
    path("doctors/", AdminDoctorListView.as_view()),
    path("doctor-assignments/", AdminDoctorAssignmentView.as_view()),
    path("meetings/", AdminMeetingListView.as_view()),
]
