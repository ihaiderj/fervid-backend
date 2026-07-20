"""Local or S3/R2 file storage helpers.

When STORAGE_BACKEND=s3, files are stored in the configured bucket and
durable public HTTPS URLs are returned (requires a public R2/custom domain).
"""

from __future__ import annotations

import mimetypes
import os
import tempfile
import uuid
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import urlparse

from django.conf import settings
from django.core.files.storage import default_storage


def uses_remote_storage() -> bool:
    return getattr(settings, "STORAGE_BACKEND", "local") == "s3"


def _content_type_for_name(name: str, fallback: str = "application/octet-stream") -> str:
    guessed, _ = mimetypes.guess_type(name)
    return guessed or fallback


def public_media_url(key: str) -> str:
    """Return the durable public URL for an object key / relative media path."""
    key = key.lstrip("/")
    if uses_remote_storage():
        custom = (getattr(settings, "AWS_S3_CUSTOM_DOMAIN", None) or "").strip().rstrip("/")
        if custom:
            if custom.startswith("http://") or custom.startswith("https://"):
                return f"{custom}/{key}"
            return f"https://{custom}/{key}"
        return default_storage.url(key)

    media_url = settings.MEDIA_URL.rstrip("/")
    return f"{media_url}/{key}"


def key_from_media_url(url: str) -> str | None:
    """Best-effort extract of storage key from a stored media URL."""
    if not url:
        return None
    value = url.strip()

    custom = (getattr(settings, "AWS_S3_CUSTOM_DOMAIN", None) or "").strip().rstrip("/")
    if custom:
        bare = custom
        if bare.startswith("https://"):
            bare = bare[len("https://") :]
        elif bare.startswith("http://"):
            bare = bare[len("http://") :]
        for prefix in (
            f"https://{bare}/",
            f"http://{bare}/",
            f"{bare}/",
            f"{custom}/",
        ):
            if value.startswith(prefix):
                return value[len(prefix) :].lstrip("/")

    media_url = settings.MEDIA_URL.rstrip("/")
    if media_url and value.startswith(media_url):
        return value[len(media_url) :].lstrip("/")
    if value.startswith("/media/"):
        return value[len("/media/") :]

    if value.startswith(("http://", "https://")):
        path = urlparse(value).path.lstrip("/")
        bucket = getattr(settings, "AWS_STORAGE_BUCKET_NAME", "") or ""
        if bucket and path.startswith(f"{bucket}/"):
            return path[len(bucket) + 1 :]
        return path or None

    return value.lstrip("/")


def _s3_client():
    import boto3
    from botocore.client import Config

    return boto3.client(
        "s3",
        endpoint_url=getattr(settings, "AWS_S3_ENDPOINT_URL", None) or None,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=getattr(settings, "AWS_S3_REGION_NAME", None) or "auto",
        config=Config(signature_version="s3v4"),
    )


def _upload_fileobj(fileobj, key: str, content_type: str) -> None:
    client = _s3_client()
    fileobj.seek(0)
    client.upload_fileobj(
        fileobj,
        settings.AWS_STORAGE_BUCKET_NAME,
        key,
        ExtraArgs={"ContentType": content_type},
    )


def _upload_bytes(data: bytes, key: str, content_type: str) -> None:
    client = _s3_client()
    client.put_object(
        Bucket=settings.AWS_STORAGE_BUCKET_NAME,
        Key=key,
        Body=data,
        ContentType=content_type,
    )


def save_uploaded_file(uploaded_file, subfolder: str) -> str:
    """Save an uploaded Django file and return a durable URL for the DB."""
    ext = os.path.splitext(uploaded_file.name)[1].lower()
    filename = f"{uuid.uuid4()}{ext}"
    key = f"{subfolder.strip('/')}/{filename}"
    content_type = getattr(uploaded_file, "content_type", None) or _content_type_for_name(
        uploaded_file.name
    )

    uploaded_file.seek(0)
    if uses_remote_storage():
        _upload_fileobj(uploaded_file, key, content_type)
        return public_media_url(key)

    dest_dir = os.path.join(settings.MEDIA_ROOT, subfolder)
    os.makedirs(dest_dir, exist_ok=True)
    dest_path = os.path.join(dest_dir, filename)
    with open(dest_path, "wb+") as f:
        for chunk in uploaded_file.chunks():
            f.write(chunk)
    return public_media_url(key)


def save_bytes(data: bytes, key: str, content_type: str | None = None) -> str:
    """Save raw bytes at key and return public URL."""
    key = key.lstrip("/")
    ctype = content_type or _content_type_for_name(key)
    if uses_remote_storage():
        _upload_bytes(data, key, ctype)
        return public_media_url(key)

    dest_path = Path(settings.MEDIA_ROOT) / key
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    dest_path.write_bytes(data)
    return public_media_url(key)


def delete_by_url(url: str) -> None:
    key = key_from_media_url(url)
    if not key:
        return
    if uses_remote_storage():
        try:
            _s3_client().delete_object(Bucket=settings.AWS_STORAGE_BUCKET_NAME, Key=key)
        except Exception:
            pass
        return
    full_path = Path(settings.MEDIA_ROOT) / key
    if full_path.exists():
        full_path.unlink()


def object_exists(key: str) -> bool:
    key = key.lstrip("/")
    if uses_remote_storage():
        try:
            _s3_client().head_object(Bucket=settings.AWS_STORAGE_BUCKET_NAME, Key=key)
            return True
        except Exception:
            return False
    return (Path(settings.MEDIA_ROOT) / key).exists()


def prefix_has_objects(prefix: str) -> bool:
    prefix = prefix.lstrip("/")
    if not prefix.endswith("/"):
        prefix = f"{prefix}/"
    if uses_remote_storage():
        try:
            resp = _s3_client().list_objects_v2(
                Bucket=settings.AWS_STORAGE_BUCKET_NAME,
                Prefix=prefix,
                MaxKeys=1,
            )
            return bool(resp.get("Contents"))
        except Exception:
            return False
    local = Path(settings.MEDIA_ROOT) / prefix.rstrip("/")
    return local.exists() and any(local.glob("*.*"))


def list_prefix_basenames(prefix: str, extensions: set[str] | None = None) -> list[str]:
    """Return sorted base filenames under a storage prefix."""
    prefix = prefix.lstrip("/")
    if not prefix.endswith("/"):
        prefix = f"{prefix}/"
    exts = {e.lower() if e.startswith(".") else f".{e.lower()}" for e in (extensions or set())}

    names: list[str] = []
    if uses_remote_storage():
        try:
            client = _s3_client()
            token = None
            while True:
                kwargs = {
                    "Bucket": settings.AWS_STORAGE_BUCKET_NAME,
                    "Prefix": prefix,
                }
                if token:
                    kwargs["ContinuationToken"] = token
                resp = client.list_objects_v2(**kwargs)
                for obj in resp.get("Contents") or []:
                    key = obj.get("Key") or ""
                    base = os.path.basename(key)
                    if not base or base.startswith("."):
                        continue
                    if exts and Path(base).suffix.lower() not in exts:
                        continue
                    names.append(base)
                if not resp.get("IsTruncated"):
                    break
                token = resp.get("NextContinuationToken")
        except Exception:
            return []
        return sorted(set(names))

    local = Path(settings.MEDIA_ROOT) / prefix.rstrip("/")
    if not local.exists():
        return []
    for path in local.iterdir():
        if not path.is_file() or path.name.startswith("."):
            continue
        if exts and path.suffix.lower() not in exts:
            continue
        names.append(path.name)
    return sorted(set(names))


@contextmanager
def open_by_url(url: str):
    """
    Yield a readable binary file for a stored media URL.
    Downloads remote objects to a temp file when using S3/R2.
    """
    key = key_from_media_url(url)
    if not key:
        raise FileNotFoundError("Invalid media URL")

    if uses_remote_storage():
        suffix = Path(key).suffix or ".bin"
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        tmp_path = tmp.name
        tmp.close()
        try:
            _s3_client().download_file(settings.AWS_STORAGE_BUCKET_NAME, key, tmp_path)
            with open(tmp_path, "rb") as f:
                yield f
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
        return

    full_path = Path(settings.MEDIA_ROOT) / key
    if not full_path.exists():
        raise FileNotFoundError(full_path)
    with open(full_path, "rb") as f:
        yield f
