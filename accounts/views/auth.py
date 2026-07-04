from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView

from accounts.models import User
from accounts.serializers import UserSerializer
from core.mixins import APIResponseMixin


class LoginView(APIResponseMixin, APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get("email", "").strip().lower()
        password = request.data.get("password", "")

        if not email or not password:
            return self.error("Email and password are required", code="MISSING_CREDENTIALS")

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return self.error("Invalid credentials", code="INVALID_CREDENTIALS", status_code=401)

        if not user.is_active:
            return self.error("Account is deactivated", code="ACCOUNT_INACTIVE", status_code=403)

        if not user.check_password(password):
            return self.error("Invalid credentials", code="INVALID_CREDENTIALS", status_code=401)

        refresh = RefreshToken.for_user(user)
        return self.success(
            {
                "access_token": str(refresh.access_token),
                "refresh_token": str(refresh),
                "user": UserSerializer(user).data,
            }
        )


class LogoutView(APIResponseMixin, APIView):
    def post(self, request):
        return self.success(message="Logged out successfully")


class MeView(APIResponseMixin, APIView):
    def get(self, request):
        return self.success(UserSerializer(request.user).data)


class RefreshTokenView(TokenRefreshView):
    pass
