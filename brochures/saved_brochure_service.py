import re
import uuid

from django.utils import timezone

from brochures.models import SavedBrochure
from core.soft_delete import soft_delete_instance

_TIMESTAMP_SUFFIX = re.compile(r"_\d+$")


def canonical_brochure_id(brochure_id) -> str:
    """Strip mobile download suffix (e.g. uuid_1783408226503 -> uuid)."""
    if brochure_id is None:
        return ""
    value = str(brochure_id).strip()
    if not value:
        return ""
    return _TIMESTAMP_SUFFIX.sub("", value)


def get_saved_brochure_for_mr(mr, identifier):
    """Find by saved row PK or canonical brochure_id (with or without suffix)."""
    if identifier is None:
        return None

    identifier = str(identifier).strip()
    if not identifier:
        return None

    try:
        uuid.UUID(identifier)
        saved = SavedBrochure.objects.filter(mr=mr, id=identifier).first()
        if saved:
            return saved
    except (ValueError, AttributeError, TypeError):
        pass

    canonical = canonical_brochure_id(identifier)
    if not canonical:
        return None

    saved = SavedBrochure.objects.filter(mr=mr, brochure_id=canonical).order_by(
        "-last_accessed"
    ).first()
    if saved:
        return saved

    for row in SavedBrochure.objects.filter(mr=mr, brochure_id__startswith=f"{canonical}_"):
        if canonical_brochure_id(row.brochure_id) == canonical:
            return row

    return None


def _mark_saved_deleted(saved):
    soft_delete_instance(saved, "last_accessed")


def upsert_saved_brochure(mr, *, brochure_id, **fields):
    canonical = canonical_brochure_id(brochure_id)
    if not canonical:
        raise ValueError("brochure_id is required")

    if fields.pop("is_deleted", False):
        saved = get_saved_brochure_for_mr(mr, canonical)
        if saved:
            _mark_saved_deleted(saved)
        return saved, False

    existing = get_saved_brochure_for_mr(mr, canonical)
    defaults = {
        "brochure_id": canonical,
        "brochure_title": fields.get("brochure_title", ""),
        "custom_title": fields.get("custom_title", ""),
        "original_brochure_data": fields.get("original_brochure_data", {}),
        "is_deleted": False,
    }

    if existing:
        for key, value in defaults.items():
            if key == "brochure_title" and not value:
                continue
            if key == "original_brochure_data" and not value:
                continue
            setattr(existing, key, value)
        existing.last_accessed = timezone.now()
        existing.save()
        return existing, False

    saved = SavedBrochure.objects.create(mr=mr, **defaults)
    return saved, True


def soft_delete_saved_brochure(mr, *, brochure_id=None, server_id=None):
    saved = None
    if server_id:
        saved = SavedBrochure.objects.filter(mr=mr, id=server_id).first()
    if not saved and brochure_id is not None:
        saved = get_saved_brochure_for_mr(mr, brochure_id)
    if not saved:
        return None
    _mark_saved_deleted(saved)
    return saved
