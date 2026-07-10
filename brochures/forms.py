from django import forms

from brochures.models import Brochure

ALLOWED_EXTENSIONS = {".pdf", ".zip"}
ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "application/zip",
    "application/x-zip-compressed",
}


class BrochureAdminForm(forms.ModelForm):
    upload_file = forms.FileField(
        required=False,
        label="Upload file",
        help_text="PDF or ZIP only. All file details are filled in automatically.",
    )

    class Meta:
        model = Brochure
        fields = (
            "title",
            "category_ref",
            "description",
            "status",
            "is_public",
            "tags",
            "version",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.pk:
            self.fields["upload_file"].required = True

    def clean_upload_file(self):
        uploaded = self.cleaned_data.get("upload_file")
        if not uploaded:
            return uploaded

        ext = "." + uploaded.name.rsplit(".", 1)[-1].lower() if "." in uploaded.name else ""
        content_type = (uploaded.content_type or "").lower()
        if ext not in ALLOWED_EXTENSIONS and content_type not in ALLOWED_CONTENT_TYPES:
            raise forms.ValidationError("Only PDF and ZIP files are allowed.")

        return uploaded

    def clean(self):
        cleaned = super().clean()
        upload = cleaned.get("upload_file")

        if not self.instance.pk and not upload:
            raise forms.ValidationError("Please upload a brochure file.")

        if self.instance.pk and not upload and not self.instance.file_url:
            raise forms.ValidationError("Please upload a brochure file.")

        return cleaned
