from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from import_export.admin import ImportExportModelAdmin

from accounts.models import MRPermission, User, UserSession

MR_PERMISSION_TYPES = (
    "upload_brochures",
    "manage_doctors",
    "schedule_meetings",
)


class MRPermissionInline(admin.TabularInline):
    model = MRPermission
    fk_name = "mr"
    extra = 0
    verbose_name_plural = "MR permissions"

    def get_extra(self, request, obj=None, **kwargs):
        if obj is None:
            return len(MR_PERMISSION_TYPES)
        if not obj.mr_permissions.exists():
            return len(MR_PERMISSION_TYPES)
        return 0

    def get_formset(self, request, obj=None, **kwargs):
        formset_class = super().get_formset(request, obj, **kwargs)
        show_defaults = obj is None or not obj.mr_permissions.exists()
        if not show_defaults:
            return formset_class

        initial = [
            {
                "permission_type": perm_type,
                "is_granted": True,
                "granted_by": request.user.pk,
            }
            for perm_type in MR_PERMISSION_TYPES
        ]

        class PrefillFormSet(formset_class):
            def __init__(self, *args, **kw):
                kw.setdefault("initial", initial)
                super().__init__(*args, **kw)
                # Ensure empty extra forms show granted_by as current admin.
                for form in self.forms:
                    if not form.instance.pk and not form.initial.get("granted_by"):
                        form.initial["granted_by"] = request.user.pk
                    if not form.instance.pk and form.initial.get("is_granted") is None:
                        form.initial["is_granted"] = True

        return PrefillFormSet

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "granted_by":
            kwargs["initial"] = request.user
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(User)
class UserAdmin(BaseUserAdmin, ImportExportModelAdmin):
    list_display = (
        "email",
        "full_name",
        "role",
        "is_active",
        "can_upload_brochures",
        "can_manage_doctors",
        "can_schedule_meetings",
        "created_at",
    )
    list_filter = (
        "role",
        "is_active",
        "can_upload_brochures",
        "can_manage_doctors",
        "can_schedule_meetings",
    )
    search_fields = ("email", "first_name", "last_name", "phone")
    ordering = ("-created_at",)
    inlines = [MRPermissionInline]
    readonly_fields = ("id", "created_at", "updated_at", "last_login")

    fieldsets = (
        (None, {"fields": ("id", "email", "password")}),
        (
            "Personal",
            {
                "fields": (
                    "first_name",
                    "last_name",
                    "phone",
                    "address",
                    "profile_image_url",
                )
            },
        ),
        (
            "Role & Permissions",
            {
                "description": (
                    "MR permission rows below are the source of truth. "
                    "After save, Can upload / manage / schedule checkboxes "
                    "are synced from granted MR permissions."
                ),
                "fields": (
                    "role",
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "can_upload_brochures",
                    "can_manage_doctors",
                    "can_schedule_meetings",
                    "permissions",
                ),
            },
        ),
        ("Timestamps", {"fields": ("created_at", "updated_at", "last_login")}),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "password1",
                    "password2",
                    "role",
                    "first_name",
                    "last_name",
                    "can_upload_brochures",
                    "can_manage_doctors",
                    "can_schedule_meetings",
                ),
            },
        ),
    )

    actions = ["deactivate_users"]

    def get_changeform_initial_data(self, request):
        return {
            "role": User.Role.MR,
            "can_upload_brochures": True,
            "can_manage_doctors": True,
            "can_schedule_meetings": True,
        }

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        user = form.instance

        # Extra forms with only initial data are often skipped as "unchanged".
        # Ensure new MRs get the three default granted permissions.
        if user.role == User.Role.MR and not user.mr_permissions.exists():
            for perm_type in MR_PERMISSION_TYPES:
                MRPermission.objects.get_or_create(
                    mr=user,
                    permission_type=perm_type,
                    defaults={
                        "is_granted": True,
                        "granted_by": request.user,
                    },
                )

        # Fill blank granted_by on any saved rows.
        user.mr_permissions.filter(granted_by__isnull=True).update(
            granted_by=request.user
        )

        self._sync_can_flags_from_mr_permissions(user, request.user)

    def _sync_can_flags_from_mr_permissions(self, user, actor):
        """Keep User.can_* in sync with granted MRPermission rows."""
        if not user.mr_permissions.exists():
            return

        granted = set(
            user.mr_permissions.filter(is_granted=True).values_list(
                "permission_type", flat=True
            )
        )
        user.can_upload_brochures = "upload_brochures" in granted
        user.can_manage_doctors = "manage_doctors" in granted
        user.can_schedule_meetings = "schedule_meetings" in granted
        user.save(
            update_fields=[
                "can_upload_brochures",
                "can_manage_doctors",
                "can_schedule_meetings",
                "updated_at",
            ]
        )

    @admin.action(description="Deactivate selected users")
    def deactivate_users(self, request, queryset):
        queryset.update(is_active=False)


@admin.register(MRPermission)
class MRPermissionAdmin(admin.ModelAdmin):
    list_display = ("mr", "permission_type", "is_granted", "granted_by", "expires_at")
    list_filter = ("permission_type", "is_granted")
    search_fields = ("mr__email", "mr__first_name", "mr__last_name")

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "granted_by":
            kwargs["initial"] = request.user
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def save_model(self, request, obj, form, change):
        if not obj.granted_by_id:
            obj.granted_by = request.user
        super().save_model(request, obj, form, change)
        # Keep User.can_* aligned when editing permissions outside the user form.
        mr = obj.mr
        granted = set(
            mr.mr_permissions.filter(is_granted=True).values_list(
                "permission_type", flat=True
            )
        )
        mr.can_upload_brochures = "upload_brochures" in granted
        mr.can_manage_doctors = "manage_doctors" in granted
        mr.can_schedule_meetings = "schedule_meetings" in granted
        mr.save(
            update_fields=[
                "can_upload_brochures",
                "can_manage_doctors",
                "can_schedule_meetings",
                "updated_at",
            ]
        )


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
