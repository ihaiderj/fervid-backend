from django.urls import path

from accounts.views.sessions import SessionRegisterView

urlpatterns = [
    path("register/", SessionRegisterView.as_view(), name="session-register"),
]
