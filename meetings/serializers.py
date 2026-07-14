from rest_framework import serializers

from meetings.models import Meeting, MeetingFollowUp, MeetingSlideNote


class SlideNoteSerializer(serializers.ModelSerializer):
    note_id = serializers.UUIDField(source="id")

    class Meta:
        model = MeetingSlideNote
        fields = [
            "note_id",
            "slide_id",
            "slide_title",
            "slide_order",
            "note_text",
            "brochure_id",
            "created_at",
            "updated_at",
        ]


class MeetingFollowUpSerializer(serializers.ModelSerializer):
    follow_up_id = serializers.UUIDField(source="id")

    class Meta:
        model = MeetingFollowUp
        fields = [
            "follow_up_id",
            "meeting_id",
            "follow_up_date",
            "follow_up_time",
            "follow_up_notes",
            "status",
            "sequence_number",
            "created_at",
            "updated_at",
        ]


class MeetingSerializer(serializers.ModelSerializer):
    mr_name = serializers.SerializerMethodField()
    doctor_name = serializers.SerializerMethodField()
    hospital = serializers.CharField(source="doctor.hospital", read_only=True)
    brochure_title = serializers.SerializerMethodField()

    class Meta:
        model = Meeting
        fields = [
            "id",
            "title",
            "mr_name",
            "doctor_name",
            "hospital",
            "scheduled_date",
            "duration_minutes",
            "status",
            "location",
            "follow_up_required",
            "brochure_title",
            "created_at",
        ]

    def get_mr_name(self, obj):
        return obj.mr.full_name

    def get_doctor_name(self, obj):
        return f"Dr. {obj.doctor.first_name} {obj.doctor.last_name}"

    def get_brochure_title(self, obj):
        return obj.brochure_title


class MRMeetingSerializer(serializers.ModelSerializer):
    meeting_id = serializers.UUIDField(source="id", read_only=True)
    doctor_name = serializers.SerializerMethodField()
    doctor_specialty = serializers.CharField(source="doctor.specialty", read_only=True)
    hospital = serializers.CharField(source="doctor.hospital", read_only=True)
    brochure_title = serializers.SerializerMethodField()
    brochure_id = serializers.SerializerMethodField()
    notes_count = serializers.SerializerMethodField()
    last_note_date = serializers.SerializerMethodField()
    profile_image_url = serializers.CharField(source="doctor.profile_image_url", read_only=True)

    class Meta:
        model = Meeting
        fields = [
            "meeting_id",
            "id",
            "title",
            "doctor_id",
            "doctor_name",
            "doctor_specialty",
            "hospital",
            "scheduled_date",
            "duration_minutes",
            "status",
            "purpose",
            "notes",
            "brochure_id",
            "brochure_title",
            "notes_count",
            "last_note_date",
            "follow_up_required",
            "follow_up_date",
            "follow_up_time",
            "follow_up_notes",
            "profile_image_url",
            "created_at",
            "updated_at",
        ]

    def get_doctor_name(self, obj):
        return f"Dr. {obj.doctor.first_name} {obj.doctor.last_name}"

    def get_brochure_title(self, obj):
        return obj.brochure_title

    def get_brochure_id(self, obj):
        if obj.brochure_id:
            return str(obj.brochure_id)
        slides = obj.presentation_slides or {}
        brochure_id = slides.get("brochure_id")
        return str(brochure_id) if brochure_id else None

    def get_notes_count(self, obj):
        return obj.slide_notes.filter(is_deleted=False).count()

    def get_last_note_date(self, obj):
        note = obj.slide_notes.filter(is_deleted=False).order_by("-updated_at").first()
        return note.updated_at if note else None


class CreateMeetingSerializer(serializers.Serializer):
    doctor_id = serializers.UUIDField()
    brochure_id = serializers.UUIDField(required=False, allow_null=True)
    brochure_title = serializers.CharField(required=False, allow_blank=True)
    title = serializers.CharField(max_length=255)
    purpose = serializers.CharField(required=False, allow_blank=True)
    scheduled_date = serializers.DateTimeField(required=False)
    duration_minutes = serializers.IntegerField(default=30)
    location = serializers.CharField(required=False, allow_blank=True)
    notes = serializers.CharField(required=False, allow_blank=True)


class UpdateMeetingSerializer(serializers.Serializer):
    doctor_id = serializers.UUIDField(required=False)
    title = serializers.CharField(required=False)
    scheduled_date = serializers.DateTimeField(required=False)
    duration_minutes = serializers.IntegerField(required=False)
    status = serializers.CharField(required=False)
    location = serializers.CharField(required=False, allow_blank=True)
    notes = serializers.CharField(required=False, allow_blank=True)
    purpose = serializers.CharField(required=False, allow_blank=True)


class AddSlideNoteSerializer(serializers.Serializer):
    slide_id = serializers.CharField()
    slide_title = serializers.CharField(required=False, allow_blank=True)
    slide_order = serializers.IntegerField(default=0)
    brochure_id = serializers.CharField(required=False, allow_blank=True)
    note_text = serializers.CharField()


class CreateFollowUpSerializer(serializers.Serializer):
    follow_up_date = serializers.DateTimeField()
    follow_up_time = serializers.CharField(required=False, allow_blank=True)
    follow_up_notes = serializers.CharField(required=False, allow_blank=True)
    status = serializers.CharField(required=False, default="scheduled")


class LegacyFollowUpSerializer(serializers.Serializer):
    follow_up_date = serializers.DateTimeField(required=False, allow_null=True)
    follow_up_time = serializers.CharField(required=False, allow_blank=True)
    follow_up_notes = serializers.CharField(required=False, allow_blank=True)
    follow_up_required = serializers.BooleanField(required=False)


class MRUpcomingMeetingSerializer(serializers.ModelSerializer):
    meeting_id = serializers.UUIDField(source="id")
    doctor_name = serializers.SerializerMethodField()
    hospital = serializers.CharField(source="doctor.hospital")

    class Meta:
        model = Meeting
        fields = ["meeting_id", "doctor_name", "hospital", "scheduled_date", "status", "notes"]

    def get_doctor_name(self, obj):
        return f"Dr. {obj.doctor.first_name} {obj.doctor.last_name}"
