import os
import uuid

from django.conf import settings


def save_uploaded_file(uploaded_file, subfolder):
    ext = os.path.splitext(uploaded_file.name)[1].lower()
    filename = f"{uuid.uuid4()}{ext}"
    dest_dir = os.path.join(settings.MEDIA_ROOT, subfolder)
    os.makedirs(dest_dir, exist_ok=True)
    dest_path = os.path.join(dest_dir, filename)
    with open(dest_path, "wb+") as f:
        for chunk in uploaded_file.chunks():
            f.write(chunk)
    media_url = settings.MEDIA_URL.rstrip("/")
    return f"{media_url}/{subfolder}/{filename}"
