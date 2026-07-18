from django import forms

from doctors.models import Doctor

ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
ALLOWED_IMAGE_CONTENT_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/gif",
}


class DoctorAdminForm(forms.ModelForm):
    upload_profile_image = forms.ImageField(
        required=False,
        label="Profile photo",
        help_text="Upload JPG, PNG, WEBP, or GIF. Saved to the server automatically.",
    )

    class Meta:
        model = Doctor
        fields = (
            "first_name",
            "last_name",
            "email",
            "phone",
            "specialty",
            "hospital",
            "location",
            "notes",
            "relationship_status",
            "meetings_count",
            "last_meeting_date",
            "next_appointment",
            "is_deleted",
        )

    def clean_upload_profile_image(self):
        uploaded = self.cleaned_data.get("upload_profile_image")
        if not uploaded:
            return uploaded

        ext = "." + uploaded.name.rsplit(".", 1)[-1].lower() if "." in uploaded.name else ""
        content_type = (uploaded.content_type or "").lower()
        if ext not in ALLOWED_IMAGE_EXTENSIONS and content_type not in ALLOWED_IMAGE_CONTENT_TYPES:
            raise forms.ValidationError("Only image files (JPG, PNG, WEBP, GIF) are allowed.")

        return uploaded
