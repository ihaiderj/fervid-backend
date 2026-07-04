from rest_framework import serializers

from activity.models import ActivityLog


class ActivityLogSerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField()

    class Meta:
        model = ActivityLog
        fields = [
            "id",
            "action",
            "activity_type",
            "entity_type",
            "entity_id",
            "description",
            "details",
            "metadata",
            "user_name",
            "created_at",
        ]

    def get_user_name(self, obj):
        return obj.user.full_name if obj.user else "System"


class CreateActivityLogSerializer(serializers.Serializer):
    action = serializers.CharField(required=False, allow_blank=True)
    activity_type = serializers.CharField(required=False, allow_blank=True)
    entity_type = serializers.CharField(required=False, allow_blank=True)
    entity_id = serializers.UUIDField(required=False, allow_null=True)
    description = serializers.CharField(required=False, allow_blank=True)
    details = serializers.JSONField(required=False)
    metadata = serializers.JSONField(required=False)
    user_id = serializers.UUIDField(required=False, allow_null=True)
