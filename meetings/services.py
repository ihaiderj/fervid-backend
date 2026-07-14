from doctors.models import Doctor
from meetings.models import Meeting


def refresh_doctor_meetings_count(doctor_id):
    """Keep Doctor.meetings_count in sync with non-deleted meetings."""
    if not doctor_id:
        return
    count = Meeting.objects.filter(doctor_id=doctor_id, is_deleted=False).count()
    Doctor.objects.filter(id=doctor_id).update(meetings_count=count)
