from django.contrib import admin
from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

import core.admin_dashboard  # noqa: F401 — registers custom admin index

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/auth/", include("accounts.urls.auth")),
    path("api/sessions/", include("accounts.urls.sessions")),
    path("api/admin/", include("accounts.urls.admin")),
    path("api/mr/", include("accounts.urls.mr")),
    path("api/activity-logs/", include("activity.urls")),
    path("api/sync/", include("sync.urls")),
    path("api/files/", include("brochures.urls.files")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

admin.site.site_header = "Fervid Admin"
admin.site.site_title = "Fervid"
admin.site.index_title = "Medical Representative Platform"
