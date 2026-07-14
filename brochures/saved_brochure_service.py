import re
import uuid

from django.utils import timezone

from brochures.models import SavedBrochure
from core.soft_delete import soft_delete_instance

# Mobile may append download suffix to brochure_id by mistake; strip for source ID only.
_TIMESTAMP_SUFFIX = re.compile(r"_\d+$")


def canonical_brochure_id(brochure_id) -> str:
    """Normalize source admin brochure UUID (strip accidental _timestamp suffix)."""
    if brochure_id is None:
        return ""
    value = str(brochure_id).strip()
    if not value:
        return ""
    return _TIMESTAMP_SUFFIX.sub("", value)


def get_saved_brochure_by_id(mr, saved_brochure_id):
    """Look up one saved copy by its server primary key."""
    if saved_brochure_id is None:
        return None
    try:
        uuid.UUID(str(saved_brochure_id))
    except (ValueError, AttributeError, TypeError):
        return None
    return SavedBrochure.objects.filter(mr=mr, id=saved_brochure_id).first()


def create_saved_brochure(mr, *, brochure_id, **fields):
    """Always insert a new saved copy (multiple copies per source brochure allowed)."""
    canonical = canonical_brochure_id(brochure_id)
    if not canonical:
        raise ValueError("brochure_id is required")

    return SavedBrochure.objects.create(
        mr=mr,
        brochure_id=canonical,
        brochure_title=fields.get("brochure_title", ""),
        custom_title=fields.get("custom_title", ""),
        original_brochure_data=fields.get("original_brochure_data", {}),
        is_deleted=False,
    )


def update_saved_brochure(mr, saved_brochure_id, **fields):
    saved = get_saved_brochure_by_id(mr, saved_brochure_id)
    if not saved or saved.is_deleted:
        return None
    if "custom_title" in fields:
        saved.custom_title = fields["custom_title"]
    if fields.get("brochure_title"):
        saved.brochure_title = fields["brochure_title"]
    if fields.get("original_brochure_data"):
        saved.original_brochure_data = fields["original_brochure_data"]
    saved.last_accessed = timezone.now()
    saved.save()
    return saved


def soft_delete_saved_brochure(mr, *, server_id):
    """Soft-delete one saved copy by its server row id."""
    saved = get_saved_brochure_by_id(mr, server_id)
    if not saved:
        return None
    soft_delete_instance(saved, "last_accessed")
    return saved
