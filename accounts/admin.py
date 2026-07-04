from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from import_export.admin import ImportExportModelAdmin

from accounts.models import MRPermission, User, UserSession


class MRPermissionInline(admin.TabularInline):
    model = MRPermission
    extra = 0
    fk_name = "mr"


@admin.register(User)
class UserAdmin(BaseUserAdmin, ImportExportModelAdmin):
    list_display = (
        "email",
        "full_name",
        "role",
        "is_active",
        "can_upload_brochures",
        "can_manage_doctors",
        "created_at",
    )
    list_filter = ("role", "is_active", "can_upload_brochures", "can_manage_doctors")
    search_fields = ("email", "first_name", "last_name", "phone")
    ordering = ("-created_at",)
    inlines = [MRPermissionInline]
    readonly_fields = ("id", "created_at", "updated_at", "last_login")

    fieldsets = (
        (None, {"fields": ("id", "email", "password")}),
        ("Personal", {"fields": ("first_name", "last_name", "phone", "address", "profile_image_url")}),
        ("Role & Permissions", {
            "fields": (
                "role",
                "is_active",
                "is_staff",
                "is_superuser",
                "can_upload_brochures",
                "can_manage_doctors",
                "can_schedule_meetings",
                "permissions",
            )
        }),
        ("Timestamps", {"fields": ("created_at", "updated_at", "last_login")}),
    )

    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "password1", "password2", "role", "first_name", "last_name"),
        }),
    )

    actions = ["deactivate_users"]

    @admin.action(description="Deactivate selected users")
    def deactivate_users(self, request, queryset):
        queryset.update(is_active=False)


@admin.register(MRPermission)
class MRPermissionAdmin(admin.ModelAdmin):
    list_display = ("mr", "permission_type", "is_granted", "granted_by", "expires_at")
    list_filter = ("permission_type", "is_granted")
    search_fields = ("mr__email", "mr__first_name", "mr__last_name")


@admin.register(UserSession)
class UserSessionAdmin(admin.ModelAdmin):
    list_display = ("user", "device_id", "is_active", "login_time", "last_activity")
    list_filter = ("is_active",)
    search_fields = ("user__email", "device_id")
    actions = ["force_logout"]

    @admin.action(description="Force logout (deactivate session)")
    def force_logout(self, request, queryset):
        from django.utils import timezone
        queryset.update(is_active=False, ended_at=timezone.now())
