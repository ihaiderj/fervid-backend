import uuid

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email is required")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("role", "admin")
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("first_name", "Admin")
        extra_fields.setdefault("last_name", "User")
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    class Role(models.TextChoices):
        ADMIN = "admin", "Admin"
        MR = "mr", "Medical Representative"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(max_length=255, unique=True)
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.MR)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    phone = models.CharField(max_length=20, blank=True, default="")
    profile_image_url = models.TextField(blank=True, default="")
    address = models.TextField(blank=True, default="")
    permissions = models.JSONField(default=dict, blank=True)
    can_upload_brochures = models.BooleanField(default=False)
    can_manage_doctors = models.BooleanField(default=False)
    can_schedule_meetings = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name"]

    class Meta:
        db_table = "users"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.email} ({self.role})"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    def has_mr_permission(self, permission_type):
        if self.role == "admin":
            return True
        flag_map = {
            "upload_brochures": self.can_upload_brochures,
            "manage_doctors": self.can_manage_doctors,
            "schedule_meetings": self.can_schedule_meetings,
        }
        if flag_map.get(permission_type):
            return True
        return self.mr_permissions.filter(
            permission_type=permission_type, is_granted=True
        ).exists()


class MRPermission(models.Model):
    PERMISSION_TYPES = (
        ("upload_brochures", "Upload Brochures"),
        ("manage_doctors", "Manage Doctors"),
        ("schedule_meetings", "Schedule Meetings"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    mr = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="mr_permissions", db_column="mr_id"
    )
    permission_type = models.CharField(max_length=50, choices=PERMISSION_TYPES)
    is_granted = models.BooleanField(default=False)
    granted_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="granted_permissions",
        db_column="granted_by",
    )
    granted_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True, default="")

    class Meta:
        db_table = "mr_permissions"
        unique_together = [("mr", "permission_type")]

    def __str__(self):
        return f"{self.mr.email} - {self.permission_type}"


class UserSession(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="sessions", db_column="user_id"
    )
    device_id = models.TextField()
    device_info = models.TextField(blank=True, default="")
    login_time = models.DateTimeField(auto_now_add=True)
    last_activity = models.DateTimeField(auto_now=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "user_sessions"
        unique_together = [("user", "device_id")]

    def __str__(self):
        return f"{self.user.email} - {self.device_id}"
