import os

from django.conf import settings
from django.core.management.base import BaseCommand

from accounts.models import User
from activity.models import SystemSetting
from brochures.models import BrochureCategory


class Command(BaseCommand):
    help = "Seed default admin user, categories, and system settings"

    def handle(self, *args, **options):
        admin_email = settings.DEFAULT_ADMIN_EMAIL
        admin_password = settings.DEFAULT_ADMIN_PASSWORD

        admin, created = User.objects.get_or_create(
            email=admin_email,
            defaults={
                "role": "admin",
                "first_name": "Admin",
                "last_name": "User",
                "is_staff": True,
                "is_superuser": True,
                "is_active": True,
            },
        )
        if created:
            admin.set_password(admin_password)
            admin.save()
            self.stdout.write(self.style.SUCCESS(f"Created admin: {admin_email}"))
        else:
            self.stdout.write(f"Admin already exists: {admin_email}")

        categories = [
            ("Cardiology", "Heart and cardiovascular system related brochures", "#ef4444"),
            ("Neurology", "Brain and nervous system related brochures", "#8b5cf6"),
            ("Oncology", "Cancer treatment and prevention brochures", "#f59e0b"),
            ("Pediatrics", "Children health and treatment brochures", "#10b981"),
            ("General Medicine", "General health and wellness brochures", "#6b7280"),
        ]
        for name, desc, color in categories:
            BrochureCategory.objects.get_or_create(
                name=name, defaults={"description": desc, "color": color}
            )

        defaults = {
            "app_name": ("Fervid", "Application display name"),
            "max_file_size": ("10485760", "Maximum file upload size in bytes (10MB)"),
            "allowed_file_types": (
                "application/pdf,application/zip,image/jpeg,image/png,image/webp",
                "Comma-separated allowed MIME types",
            ),
            "meeting_duration_default": ("30", "Default meeting duration in minutes"),
            "notification_enabled": ("true", "Enable push notifications"),
            "backup_frequency": ("daily", "Database backup frequency"),
            "session_timeout": ("3600", "Session timeout in seconds"),
        }
        for key, (value, desc) in defaults.items():
            SystemSetting.objects.get_or_create(
                setting_key=key,
                defaults={"setting_value": value, "description": desc},
            )

        os.makedirs(settings.MEDIA_ROOT, exist_ok=True)
        self.stdout.write(self.style.SUCCESS("Seed data complete"))
