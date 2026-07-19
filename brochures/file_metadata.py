import os
import uuid
import zipfile

from brochures.storage import save_bytes

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}


def format_file_size(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes} B"
    if size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    return f"{size_bytes / (1024 * 1024):.1f} MB"


def _guess_content_type(filename: str) -> str:
    ext = os.path.splitext(filename)[1].lower()
    if ext == ".pdf":
        return "application/pdf"
    if ext == ".zip":
        return "application/zip"
    return "application/octet-stream"


def _pdf_page_count(uploaded_file) -> int | None:
    try:
        from pypdf import PdfReader

        uploaded_file.seek(0)
        return len(PdfReader(uploaded_file).pages)
    except Exception:
        return None


def _zip_metadata(uploaded_file) -> tuple[int | None, str]:
    """Return slide/image count and optional thumbnail URL saved under media."""
    uploaded_file.seek(0)
    thumbnail_url = ""
    image_count = 0

    try:
        with zipfile.ZipFile(uploaded_file) as zf:
            image_names = sorted(
                n
                for n in zf.namelist()
                if not n.endswith("/")
                and os.path.splitext(n)[1].lower() in IMAGE_EXTENSIONS
            )
            image_count = len(image_names)

            if image_names:
                ext = os.path.splitext(image_names[0])[1].lower()
                thumb_name = f"{uuid.uuid4()}{ext}"
                key = f"brochures/thumbnails/{thumb_name}"
                with zf.open(image_names[0]) as src:
                    data = src.read()
                thumbnail_url = save_bytes(data, key)
    except Exception:
        pass

    return image_count or None, thumbnail_url


def apply_upload_metadata(obj, uploaded_file):
    """Populate brochure file fields from an uploaded PDF/ZIP."""
    name = uploaded_file.name
    ext = os.path.splitext(name)[1].lower()
    content_type = (uploaded_file.content_type or "").strip() or _guess_content_type(name)

    obj.file_name = name
    obj.file_type = content_type
    obj.file_size = format_file_size(uploaded_file.size)
    obj.pages = None
    obj.thumbnail_url = ""

    uploaded_file.seek(0)
    if ext == ".pdf":
        obj.pages = _pdf_page_count(uploaded_file)
    elif ext == ".zip":
        pages, thumbnail_url = _zip_metadata(uploaded_file)
        obj.pages = pages
        obj.thumbnail_url = thumbnail_url

    uploaded_file.seek(0)
