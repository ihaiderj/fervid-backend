from rest_framework import serializers

from doctors.models import Doctor, DoctorAssignment


class DoctorSerializer(serializers.ModelSerializer):
    assigned_mr_name = serializers.SerializerMethodField()

    class Meta:
        model = Doctor
        fields = [
            "id",
            "first_name",
            "last_name",
            "email",
            "phone",
            "specialty",
            "hospital",
            "location",
            "profile_image_url",
            "notes",
            "relationship_status",
            "meetings_count",
            "last_meeting_date",
            "next_appointment",
            "assigned_mr_name",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "meetings_count", "created_at", "updated_at"]

    def get_assigned_mr_name(self, obj):
        assignment = (
            obj.assignments.filter(status="active")
            .select_related("mr")
            .first()
        )
        return assignment.mr.full_name if assignment else None


class CreateDoctorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Doctor
        fields = [
            "first_name",
            "last_name",
            "email",
            "phone",
            "specialty",
            "hospital",
            "location",
            "profile_image_url",
            "notes",
        ]


class DoctorAssignmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = DoctorAssignment
        fields = [
            "id",
            "doctor_id",
            "mr_id",
            "status",
            "assigned_at",
            "notes",
        ]


class AssignDoctorSerializer(serializers.Serializer):
    doctor_id = serializers.UUIDField()
    mr_id = serializers.UUIDField()
    notes = serializers.CharField(required=False, allow_blank=True)


class MRAssignedDoctorSerializer(serializers.ModelSerializer):
    doctor_id = serializers.UUIDField(source="id")
    next_meeting_date = serializers.DateTimeField(source="next_appointment", allow_null=True)

    class Meta:
        model = Doctor
        fields = [
            "doctor_id",
            "first_name",
            "last_name",
            "specialty",
            "hospital",
            "phone",
            "email",
            "location",
            "relationship_status",
            "meetings_count",
            "last_meeting_date",
            "next_meeting_date",
            "notes",
            "profile_image_url",
            "created_at",
        ]
