from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role == "admin"
        )


class IsMR(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role == "mr"
        )


class IsAdminOrMR(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role in ("admin", "mr")
        )


class IsAdminOrReadOwn(BasePermission):
    """Admin full access; MR read/update own profile only."""

    def has_object_permission(self, request, view, obj):
        if request.user.role == "admin":
            return True
        return getattr(obj, "id", None) == request.user.id


class CanUploadBrochures(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.role == "admin":
            return True
        return user.can_upload_brochures or user.has_mr_permission("upload_brochures")


class CanManageDoctors(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.role == "admin":
            return True
        if request.method in SAFE_METHODS:
            return True
        return user.can_manage_doctors or user.has_mr_permission("manage_doctors")
