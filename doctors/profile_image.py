from django.conf import settings
from django.utils.html import format_html


def is_server_profile_image_url(url: str) -> bool:
    if not url:
        return False
    value = url.strip()
    if value.startswith("file://"):
        return False
    if value.startswith(settings.MEDIA_URL):
        return True
    if value.startswith(("http://", "https://")) and settings.MEDIA_URL.strip("/") in value:
        return True
    return value.startswith(("http://", "https://"))


def profile_image_preview_html(url: str, *, max_height: int = 48) -> str:
    if not url:
        return "—"
    if not is_server_profile_image_url(url):
        return format_html(
            '<span style="color:#999">Local device path (not on server)</span>'
        )
    return format_html(
        '<img src="{}" alt="Doctor photo" style="max-height:{}px;border-radius:4px" />',
        url,
        max_height,
    )
