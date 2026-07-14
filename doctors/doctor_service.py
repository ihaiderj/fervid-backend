from doctors.models import Doctor, DoctorAssignment
from core.soft_delete import soft_delete_instance


def soft_delete_doctor_for_mr(mr, doctor_id):
    """
    Soft-delete a doctor for an MR and deactivate their assignments.
    Used by REST delete and sync push tombstones.
    """
    doctor = Doctor.objects.filter(id=doctor_id).first()
    if not doctor or doctor.is_deleted:
        return doctor

    is_assigned = DoctorAssignment.objects.filter(doctor=doctor, mr=mr).exists()
    is_creator = doctor.created_by_id == mr.id
    if not is_assigned and not is_creator:
        return None

    soft_delete_instance(doctor, "updated_at")
    DoctorAssignment.objects.filter(doctor=doctor, status="active").update(status="inactive")
    return doctor
