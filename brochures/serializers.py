from rest_framework import serializers

from brochures.models import Brochure, BrochureCategory, BrochureSync, SavedBrochure


class BrochureCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = BrochureCategory
        fields = ["id", "name", "description", "color", "is_active", "created_at"]


class BrochureSerializer(serializers.ModelSerializer):
    category = serializers.SerializerMethodField()
    assigned_by_name = serializers.SerializerMethodField()

    class Meta:
        model = Brochure
        fields = [
            "id",
            "title",
            "category",
            "description",
            "file_url",
            "thumbnail_url",
            "file_name",
            "file_type",
            "pages",
            "file_size",
            "status",
            "download_count",
            "view_count",
            "assigned_by_name",
            "is_public",
            "tags",
            "version",
            "created_at",
        ]

    def get_category(self, obj):
        return obj.category_name

    def get_assigned_by_name(self, obj):
        if obj.assigned_by:
            return obj.assigned_by.full_name
        if obj.uploaded_by:
            return obj.uploaded_by.full_name
        return None


class CreateBrochureSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255)
    category_id = serializers.UUIDField(required=False, allow_null=True)
    category = serializers.CharField(required=False, allow_blank=True)
    description = serializers.CharField(required=False, allow_blank=True)
    file_url = serializers.CharField(required=False, allow_blank=True)
    file_name = serializers.CharField(required=False, allow_blank=True)
    file_type = serializers.CharField(required=False, allow_blank=True)
    pages = serializers.IntegerField(required=False, allow_null=True)
    file_size = serializers.CharField(required=False, allow_blank=True)
    thumbnail_url = serializers.CharField(required=False, allow_blank=True)
    tags = serializers.ListField(child=serializers.CharField(), required=False)
    is_public = serializers.BooleanField(default=True)


class MRAssignedBrochureSerializer(serializers.ModelSerializer):
    uploaded_by_name = serializers.SerializerMethodField()
    brochure_id = serializers.UUIDField(source="id")

    class Meta:
        model = Brochure
        fields = [
            "id",
            "brochure_id",
            "title",
            "category",
            "description",
            "thumbnail_url",
            "view_count",
            "download_count",
            "uploaded_by_name",
            "file_url",
            "file_name",
            "file_type",
            "created_at",
        ]

    def get_category(self, obj):
        return obj.category_name

    def get_uploaded_by_name(self, obj):
        user = obj.uploaded_by or obj.assigned_by
        return user.full_name if user else "Unknown"

    category = serializers.SerializerMethodField()


class SavedBrochureSerializer(serializers.ModelSerializer):
    class Meta:
        model = SavedBrochure
        fields = [
            "id",
            "brochure_id",
            "brochure_title",
            "custom_title",
            "original_brochure_data",
            "saved_at",
            "last_accessed",
        ]


class BrochureSyncSerializer(serializers.ModelSerializer):
    class Meta:
        model = BrochureSync
        fields = [
            "id",
            "brochure_id",
            "brochure_title",
            "brochure_data",
            "last_modified",
            "created_at",
        ]


class BrochureAnalyticsSerializer(serializers.Serializer):
    brochure_id = serializers.UUIDField()
    title = serializers.CharField()
    category = serializers.CharField()
    total_views = serializers.IntegerField()
    total_downloads = serializers.IntegerField()
    last_viewed = serializers.DateTimeField(allow_null=True)
    created_at = serializers.DateTimeField()
