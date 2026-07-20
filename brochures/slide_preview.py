"""Helpers for admin preview of saved-brochure slides/groups and doctor-linked groups."""

from __future__ import annotations

import os
import zipfile
from pathlib import Path

from django.conf import settings
from django.utils.html import format_html
from django.utils.safestring import mark_safe


def is_server_image_url(url: str) -> bool:
    if not url:
        return False
    value = str(url).strip()
    if value.startswith("file://"):
        return False
    if value.startswith(settings.MEDIA_URL):
        return True
    if value.startswith(("http://", "https://")):
        return True
    return False


def ensure_source_slides_extracted(source_brochure) -> bool:
    """
    Ensure JPG/PNG slides from the source brochure ZIP are available under
    brochure_slides/{brochure_id}/ (local media or R2).
    Returns True if slides are available for preview.
    """
    from brochures.storage import (
        open_by_url,
        prefix_has_objects,
        save_bytes,
        uses_remote_storage,
    )

    if not source_brochure or not source_brochure.file_url:
        return False

    prefix = f"brochure_slides/{source_brochure.id}"
    if prefix_has_objects(prefix):
        return True

    url = source_brochure.file_url
    # Only ZIP brochures can be expanded into slide images.
    if not str(url).lower().split("?")[0].endswith(".zip"):
        # Local relative path without .zip in URL still possible — try open anyway.
        pass

    try:
        with open_by_url(url) as zip_file:
            with zipfile.ZipFile(zip_file) as zf:
                extracted = 0
                for name in zf.namelist():
                    base = os.path.basename(name)
                    if not base:
                        continue
                    ext = Path(base).suffix.lower()
                    if ext not in {".jpg", ".jpeg", ".png", ".webp", ".gif"}:
                        continue
                    key = f"{prefix}/{base}"
                    with zf.open(name) as src:
                        save_bytes(src.read(), key)
                    extracted += 1
                if extracted == 0:
                    return False
    except Exception:
        return False

    if uses_remote_storage():
        return prefix_has_objects(prefix)

    dest_dir = Path(settings.MEDIA_ROOT) / prefix
    marker = dest_dir / ".extracted"
    try:
        marker.write_text("ok", encoding="utf-8")
    except OSError:
        pass
    return dest_dir.exists() and any(dest_dir.glob("*.*"))


def slide_image_url_from_filename(source_brochure, file_name: str) -> str:
    from brochures.storage import object_exists, public_media_url

    if not source_brochure or not file_name:
        return ""
    if not ensure_source_slides_extracted(source_brochure):
        return ""
    base = os.path.basename(file_name)
    key = f"brochure_slides/{source_brochure.id}/{base}"
    if object_exists(key):
        return public_media_url(key)

    # Case-insensitive match (local only is cheap; for R2 try common variants)
    dest_dir = Path(settings.MEDIA_ROOT) / "brochure_slides" / str(source_brochure.id)
    if dest_dir.exists():
        matches = [p for p in dest_dir.iterdir() if p.name.lower() == base.lower()]
        if matches:
            return public_media_url(f"brochure_slides/{source_brochure.id}/{matches[0].name}")
    return ""


IMAGE_SLIDE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}


def list_source_slide_filenames(source_brochure) -> list[str]:
    """Extract ZIP slides if needed, then return sorted image filenames."""
    from brochures.storage import list_prefix_basenames

    if not source_brochure or not ensure_source_slides_extracted(source_brochure):
        return []
    prefix = f"brochure_slides/{source_brochure.id}"
    return list_prefix_basenames(prefix, IMAGE_SLIDE_EXTENSIONS)


def build_source_slides_list(source_brochure) -> list[dict]:
    """Slide dicts for admin preview tables from a source brochure ZIP."""
    files = list_source_slide_filenames(source_brochure)
    return [
        {
            "id": f"source_slide_{i}",
            "title": name,
            "fileName": name,
            "order": i,
            "image_url": slide_image_url_from_filename(source_brochure, name),
        }
        for i, name in enumerate(files, start=1)
    ]


def resolve_slide_image_url(slide: dict, source_brochure=None) -> str:
    """Prefer server URL on the slide; else map fileName to extracted source slides."""
    for key in ("image_url", "imageUrl", "thumbnail_url", "thumbnailUrl"):
        value = (slide or {}).get(key) or ""
        if is_server_image_url(value):
            return value
    file_name = (slide or {}).get("fileName") or (slide or {}).get("file_name") or ""
    if source_brochure and file_name:
        return slide_image_url_from_filename(source_brochure, file_name)
    return ""


def find_brochure_syncs_for_saved(saved):
    """
    Match BrochureSync rows to a SavedBrochure.
    Only exact links — do not infer via notes (that caused false matches).
      1. sync.brochure_id == saved.id  (preferred)
      2. sync.brochure_title == saved.custom_title (or brochure_title)
    """
    from brochures.models import BrochureSync

    qs = BrochureSync.objects.filter(mr=saved.mr, is_deleted=False)
    exact = list(qs.filter(brochure_id=str(saved.id)))
    if exact:
        return exact

    titles = {t for t in (saved.custom_title, saved.brochure_title) if t}
    if titles:
        return [s for s in qs if (s.brochure_title or "") in titles]
    return []


def find_all_syncs_for_mr(mr):
    from brochures.models import BrochureSync

    return list(BrochureSync.objects.filter(mr=mr, is_deleted=False))


def sync_payload(sync):
    data = sync.brochure_data if isinstance(sync.brochure_data, dict) else {}
    slides = data.get("slides") or []
    groups = data.get("groups") or data.get("slide_groups") or []
    return {
        "slides": slides if isinstance(slides, list) else [],
        "groups": groups if isinstance(groups, list) else [],
        "data": data,
        "sync": sync,
    }


def find_slide_notes_for_saved(saved):
    from meetings.models import MeetingSlideNote

    ids = {str(saved.id), str(saved.brochure_id)}
    titles = {t for t in (saved.custom_title, saved.brochure_title) if t}
    qs = MeetingSlideNote.objects.filter(is_deleted=False).select_related("meeting")
    notes = []
    for note in qs.filter(meeting__mr=saved.mr):
        if note.brochure_id in ids:
            notes.append(note)
            continue
        if note.brochure_title and note.brochure_title in titles:
            notes.append(note)
    return notes


def _slide_id_matches(slide: dict, slide_id: str) -> bool:
    if not slide_id:
        return False
    sid = str(slide.get("id") or "")
    return sid == slide_id or sid.endswith(f"_{slide_id}") or slide_id.endswith(sid)


def find_saved_for_note(note):
    """Best SavedBrochure match for a slide note (by saved id, then title)."""
    from django.db.models import Q

    from brochures.models import SavedBrochure

    if not note or not getattr(note, "meeting_id", None):
        return None
    mr_id = note.meeting.mr_id if note.meeting_id else None
    if not mr_id:
        return None

    def _pick(qs):
        # Prefer active rows, but allow soft-deleted for preview/title resolution.
        return qs.order_by("is_deleted", "-saved_at").first()

    brochure_id = (note.brochure_id or "").strip()
    if brochure_id:
        saved = _pick(SavedBrochure.objects.filter(mr_id=mr_id, id=brochure_id))
        if saved:
            return saved
        saved = _pick(
            SavedBrochure.objects.filter(mr_id=mr_id, brochure_id=brochure_id)
        )
        if saved:
            return saved

    title = (note.brochure_title or "").strip()
    if title:
        return _pick(
            SavedBrochure.objects.filter(mr_id=mr_id).filter(
                Q(custom_title=title) | Q(brochure_title=title)
            )
        )
    return None


def _slide_matches_note(slide: dict, note) -> bool:
    slide_id = (getattr(note, "slide_id", None) or "").strip()
    if _slide_id_matches(slide, slide_id):
        return True
    # Fallback when the slide id left the sync payload: match by stored title/filename.
    stored = (getattr(note, "slide_title", None) or "").strip().lower()
    if not stored:
        return False
    file_name = (slide.get("fileName") or slide.get("file_name") or "").strip().lower()
    title = (slide.get("title") or "").strip().lower()
    if stored == title or stored == file_name:
        return True
    if file_name.startswith(stored + ".") or stored + ".jpg" == file_name:
        return True
    if stored.endswith(".jpg") and stored == file_name:
        return True
    return False


def find_sync_slide_for_note(note):
    """
    Return (slide_dict, source_brochure, sync) for a MeetingSlideNote by matching
    slide_id (or stored title/filename) against brochure_sync for the linked
    saved brochure / MR.
    """
    from brochures.models import Brochure, BrochureSync

    if not note:
        return None, None, None

    saved = find_saved_for_note(note)
    source = None
    syncs = []

    if saved:
        source = Brochure.objects.filter(id=saved.brochure_id).first()
        syncs = find_brochure_syncs_for_saved(saved)
        # Soft-deleted saved rows are skipped by find_brochure_syncs_for_saved's
        # title path via active syncs only — still match sync by saved.id.
        if not syncs:
            syncs = list(
                BrochureSync.objects.filter(
                    mr_id=saved.mr_id,
                    is_deleted=False,
                    brochure_id=str(saved.id),
                )
            )

    if not syncs and note.meeting_id and note.meeting.mr_id:
        qs = BrochureSync.objects.filter(mr_id=note.meeting.mr_id, is_deleted=False)
        brochure_id = (note.brochure_id or "").strip()
        title = (note.brochure_title or "").strip()
        if brochure_id:
            syncs = list(qs.filter(brochure_id=brochure_id))
        if not syncs and title:
            syncs = [s for s in qs if (s.brochure_title or "") == title]
        if not source and brochure_id:
            source = Brochure.objects.filter(id=brochure_id).first()

    for sync in syncs:
        for slide in sync_payload(sync)["slides"]:
            if _slide_matches_note(slide, note):
                if not source and saved:
                    source = Brochure.objects.filter(id=saved.brochure_id).first()
                return slide, source, sync

    # Source ZIP fallback even without a sync slide row.
    if not source and saved:
        source = Brochure.objects.filter(id=saved.brochure_id).first()
    return None, source, (syncs[0] if syncs else None)


def resolve_note_slide_display_title(note) -> str:
    """Prefer renamed title from brochure_sync; else stored note.slide_title."""
    slide, _, _ = find_sync_slide_for_note(note)
    if slide:
        title = (slide.get("title") or "").strip()
        file_name = (slide.get("fileName") or slide.get("file_name") or "").strip()
        if title:
            return title
        if file_name:
            return file_name
    return (note.slide_title or "").strip() or (note.slide_id or "—")


def resolve_note_slide_image_url(note) -> str:
    """Server preview URL for a slide note (sync image_url or extracted ZIP)."""
    slide, source, _ = find_sync_slide_for_note(note)
    if slide:
        url = resolve_slide_image_url(slide, source)
        if url:
            return url

    # Fallbacks: note-stored URI, or map slide_title / file-like id via source ZIP.
    uri = (getattr(note, "slide_image_uri", None) or "").strip()
    if is_server_image_url(uri):
        return uri

    if source:
        for candidate in (
            (note.slide_title or "").strip(),
            (note.slide_id or "").strip(),
        ):
            if candidate and "." in candidate:
                url = slide_image_url_from_filename(source, candidate)
                if url:
                    return url
            elif candidate:
                for ext in (".jpg", ".jpeg", ".png", ".webp"):
                    url = slide_image_url_from_filename(source, candidate + ext)
                    if url:
                        return url
    return ""


def find_groups_for_doctor(doctor):
    """Groups across brochure_sync whose doctorId or name matches this doctor."""
    from brochures.models import BrochureSync

    doctor_id = str(doctor.id)
    name_variants = {
        f"{doctor.first_name} {doctor.last_name}".strip(),
        f"Dr. {doctor.first_name} {doctor.last_name}".strip(),
        doctor.first_name,
    }
    name_variants = {n.lower() for n in name_variants if n}

    results = []
    for sync in BrochureSync.objects.filter(is_deleted=False).select_related("mr"):
        payload = sync_payload(sync)
        for group in payload["groups"]:
            gid = str(group.get("doctorId") or group.get("doctor_id") or "")
            gname = (group.get("name") or "").strip().lower()
            if gid == doctor_id or gname in name_variants:
                results.append(
                    {
                        "group": group,
                        "sync": sync,
                        "slides": payload["slides"],
                    }
                )
    return results


def thumb_html(url: str, title: str = "", max_height: int = 72) -> str:
    if url and is_server_image_url(url):
        return format_html(
            '<a href="{}" target="_blank" rel="noopener">'
            '<img src="{}" alt="{}" title="{}" '
            'style="max-height:{}px;max-width:120px;border-radius:4px;'
            'border:1px solid #ddd;object-fit:cover"/>'
            "</a>",
            url,
            url,
            title or "slide",
            title or "Open full image",
            max_height,
        )
    return format_html(
        '<span style="color:#999;font-size:12px">No server image</span>'
    )


def render_slides_table(slides, source_brochure=None, notes_by_slide=None) -> str:
    notes_by_slide = notes_by_slide or {}
    if not slides:
        return "<p style='color:#666'>No slides found for this brochure.</p>"

    rows = []
    for slide in sorted(slides, key=lambda s: s.get("order") or 0):
        slide_id = slide.get("id") or ""
        title = slide.get("title") or slide.get("fileName") or "—"
        order = slide.get("order", "")
        file_name = slide.get("fileName") or slide.get("file_name") or ""
        group_ids = slide.get("groupIds") or slide.get("groupId") or []
        if isinstance(group_ids, str):
            group_ids = [group_ids]
        img = resolve_slide_image_url(slide, source_brochure)
        note_bits = notes_by_slide.get(slide_id) or []
        notes_html = (
            "<br>".join(
                format_html(
                    "<div style='margin:4px 0;padding:6px;background:#f7f7f7;"
                    "border-radius:4px;max-width:40ch'>"
                    "<strong>{}</strong><br>{}"
                    "</div>",
                    n.get("meeting") or "",
                    n.get("text") or "",
                )
                for n in note_bits
            )
            if note_bits
            else "—"
        )
        rows.append(
            format_html(
                "<tr>"
                "<td style='padding:8px;vertical-align:top'>{}</td>"
                "<td style='padding:8px;vertical-align:top'>{}</td>"
                "<td style='padding:8px;vertical-align:top'>"
                "<strong>{}</strong><br>"
                "<span style='color:#666;font-size:11px'>{}</span><br>"
                "<span style='color:#999;font-size:11px'>{}</span>"
                "</td>"
                "<td style='padding:8px;vertical-align:top;font-size:12px'>{}</td>"
                "<td style='padding:8px;vertical-align:top'>{}</td>"
                "</tr>",
                order,
                mark_safe(thumb_html(img, title)),
                title,
                slide_id,
                file_name,
                ", ".join(group_ids) if group_ids else "—",
                mark_safe(notes_html),
            )
        )

    return mark_safe(
        "<table style='border-collapse:collapse;width:100%;max-width:1100px'>"
        "<thead><tr style='background:#f0f0f0'>"
        "<th style='padding:8px;text-align:left'>#</th>"
        "<th style='padding:8px;text-align:left'>Preview</th>"
        "<th style='padding:8px;text-align:left'>Slide</th>"
        "<th style='padding:8px;text-align:left'>Groups</th>"
        "<th style='padding:8px;text-align:left'>Notes</th>"
        "</tr></thead><tbody>"
        + "".join(str(r) for r in rows)
        + "</tbody></table>"
    )


def render_groups_table(groups, slides=None, source_brochure=None) -> str:
    slides = slides or []
    slide_map = {s.get("id"): s for s in slides if s.get("id")}
    if not groups:
        return "<p style='color:#666'>No groups created for this brochure.</p>"

    blocks = []
    for group in sorted(groups, key=lambda g: g.get("order") or 0):
        name = group.get("name") or "—"
        color = group.get("color") or "#ccc"
        slide_ids = group.get("slideIds") or group.get("slide_ids") or []
        doctor_id = group.get("doctorId") or group.get("doctor_id") or ""

        slide_cards = []
        for sid in slide_ids:
            slide = slide_map.get(sid) or {"id": sid, "title": sid}
            title = slide.get("title") or slide.get("fileName") or sid
            order = slide.get("order", "")
            file_name = slide.get("fileName") or slide.get("file_name") or ""
            img = resolve_slide_image_url(slide, source_brochure)
            slide_cards.append(
                format_html(
                    "<div style='display:inline-block;vertical-align:top;"
                    "margin:0 10px 12px 0;width:140px;text-align:center'>"
                    "<div style='margin-bottom:4px'>{}</div>"
                    "<div style='font-size:12px;font-weight:600;line-height:1.3'>"
                    "{}{}</div>"
                    "<div style='font-size:10px;color:#999;word-break:break-all'>{}</div>"
                    "</div>",
                    mark_safe(thumb_html(img, title, max_height=90)),
                    f"#{order} " if order != "" else "",
                    title,
                    file_name or sid,
                )
            )

        if not slide_cards:
            slides_html = format_html(
                "<span style='color:#666'>No slides in this group.</span>"
            )
        else:
            slides_html = mark_safe("".join(str(c) for c in slide_cards))

        blocks.append(
            format_html(
                "<div style='margin:0 0 20px 0;padding:12px;border:1px solid #e0e0e0;"
                "border-radius:6px;max-width:1100px'>"
                "<div style='margin-bottom:10px'>"
                "<span style='display:inline-block;width:12px;height:12px;"
                "border-radius:2px;background:{};margin-right:8px;"
                "vertical-align:middle'></span>"
                "<strong style='font-size:14px;vertical-align:middle'>{}</strong>"
                "<span style='margin-left:12px;color:#666;font-size:12px'>"
                "{} slides</span>"
                "<div style='margin-top:4px;font-size:12px;color:#666'>"
                "Doctor id: {}</div>"
                "</div>"
                "<div>{}</div>"
                "</div>",
                color,
                name,
                len(slide_ids),
                doctor_id or "—",
                slides_html,
            )
        )

    return mark_safe("".join(str(b) for b in blocks))


def render_notes_table(notes) -> str:
    if not notes:
        return "<p style='color:#666'>No slide notes for this brochure.</p>"

    rows = []
    for note in notes:
        meeting = note.meeting
        display_title = resolve_note_slide_display_title(note)
        img = resolve_note_slide_image_url(note)
        actions = format_html(
            '<a href="/admin/meetings/meetingslidenote/{}/change/">Edit</a>'
            ' &nbsp;|&nbsp; '
            '<a href="/admin/meetings/meetingslidenote/{}/delete/" '
            'style="color:#ba2121">Delete</a>',
            note.id,
            note.id,
        )
        rows.append(
            format_html(
                "<tr>"
                "<td style='padding:8px;vertical-align:top'>{}</td>"
                "<td style='padding:8px;vertical-align:top'>{}</td>"
                "<td style='padding:8px;vertical-align:top'>"
                "<strong>{}</strong><br>"
                "<span style='color:#999;font-size:11px'>{}</span></td>"
                "<td style='padding:8px;vertical-align:top'>{}</td>"
                "<td style='padding:8px;vertical-align:top'>{}</td>"
                "<td style='padding:8px;vertical-align:top;white-space:pre-wrap;"
                "max-width:40ch'>{}</td>"
                "<td style='padding:8px;vertical-align:top;font-size:12px'>{}</td>"
                "<td style='padding:8px;vertical-align:top;white-space:nowrap'>{}</td>"
                "</tr>",
                note.slide_order,
                mark_safe(thumb_html(img, display_title)),
                display_title,
                note.slide_id,
                note.brochure_title or "—",
                format_html(
                    '<a href="/admin/meetings/meeting/{}/change/">{}</a>',
                    meeting.id,
                    meeting.title,
                )
                if meeting
                else "—",
                note.note_text or "",
                note.updated_at.strftime("%Y-%m-%d %H:%M") if note.updated_at else "—",
                actions,
            )
        )

    return mark_safe(
        "<table style='border-collapse:collapse;width:100%;max-width:1200px'>"
        "<thead><tr style='background:#f0f0f0'>"
        "<th style='padding:8px;text-align:left'>#</th>"
        "<th style='padding:8px;text-align:left'>Preview</th>"
        "<th style='padding:8px;text-align:left'>Slide</th>"
        "<th style='padding:8px;text-align:left'>Brochure title</th>"
        "<th style='padding:8px;text-align:left'>Meeting</th>"
        "<th style='padding:8px;text-align:left'>Note</th>"
        "<th style='padding:8px;text-align:left'>Updated</th>"
        "<th style='padding:8px;text-align:left'>Actions</th>"
        "</tr></thead><tbody>"
        + "".join(str(r) for r in rows)
        + "</tbody></table>"
    )
