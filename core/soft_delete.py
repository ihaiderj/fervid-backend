from django.utils import timezone


def soft_delete_instance(instance, *timestamp_fields):
    """Soft-delete and bump sync timestamps (required when using update_fields)."""
    instance.is_deleted = True
    fields = ["is_deleted"]
    now = timezone.now()
    for field in timestamp_fields:
        if hasattr(instance, field):
            setattr(instance, field, now)
            fields.append(field)
    instance.save(update_fields=fields)
