from collections import defaultdict

from django.db import migrations


def canonical_brochure_id(brochure_id):
    import re

    value = str(brochure_id or "").strip()
    if not value:
        return ""
    return re.sub(r"_\d+$", "", value)


def normalize_saved_brochures(apps, schema_editor):
    SavedBrochure = apps.get_model("brochures", "SavedBrochure")
    groups = defaultdict(list)

    for row in SavedBrochure.objects.all().iterator():
        key = (row.mr_id, canonical_brochure_id(row.brochure_id))
        groups[key].append(row)

    for (_mr_id, canonical), rows in groups.items():
        if not canonical:
            continue

        active = [r for r in rows if not r.is_deleted]
        keeper = active[0] if active else rows[0]

        keeper.brochure_id = canonical
        keeper.save(update_fields=["brochure_id"])

        for duplicate in rows:
            if duplicate.pk == keeper.pk:
                continue
            duplicate.delete()


class Migration(migrations.Migration):
    dependencies = [
        ("brochures", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(normalize_saved_brochures, migrations.RunPython.noop),
    ]
