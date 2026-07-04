from django.urls import path

from brochures.views.files import (
    BrochureDownloadView,
    BrochureFileDeleteView,
    BrochureUploadView,
    DoctorPhotoUploadView,
)

urlpatterns = [
    path("brochures/upload/", BrochureUploadView.as_view()),
    path("brochures/<uuid:pk>/download/", BrochureDownloadView.as_view()),
    path("brochures/<uuid:pk>/", BrochureFileDeleteView.as_view()),
    path("doctor-photos/upload/", DoctorPhotoUploadView.as_view()),
]
