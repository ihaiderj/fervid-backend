from django.urls import path

from activity.views import ActivityLogView

urlpatterns = [
    path("", ActivityLogView.as_view()),
]
