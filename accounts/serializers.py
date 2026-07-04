from rest_framework import serializers

from accounts.models import MRPermission, User, UserSession


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "role",
            "first_name",
            "last_name",
            "phone",
            "profile_image_url",
            "address",
            "can_upload_brochures",
            "can_manage_doctors",
            "can_schedule_meetings",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "role", "created_at", "updated_at"]


class MRPermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = MRPermission
        fields = [
            "id",
            "permission_type",
            "is_granted",
            "granted_at",
            "expires_at",
            "notes",
        ]


class MRDataSerializer(serializers.ModelSerializer):
    doctors_count = serializers.IntegerField(read_only=True)
    meetings_count = serializers.IntegerField(read_only=True)
    permissions = MRPermissionSerializer(source="mr_permissions", many=True, read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "phone",
            "profile_image_url",
            "address",
            "is_active",
            "can_upload_brochures",
            "can_manage_doctors",
            "can_schedule_meetings",
            "doctors_count",
            "meetings_count",
            "permissions",
            "created_at",
        ]


class CreateMRSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=6)
    first_name = serializers.CharField(max_length=100)
    last_name = serializers.CharField(max_length=100)
    phone = serializers.CharField(max_length=20, required=False, allow_blank=True)
    address = serializers.CharField(required=False, allow_blank=True)
    profile_image_url = serializers.CharField(required=False, allow_blank=True)
    can_upload_brochures = serializers.BooleanField(default=False)
    can_manage_doctors = serializers.BooleanField(default=False)
    can_schedule_meetings = serializers.BooleanField(default=True)


class UpdateMRPermissionsSerializer(serializers.Serializer):
    can_upload_brochures = serializers.BooleanField(required=False)
    can_manage_doctors = serializers.BooleanField(required=False)
    can_schedule_meetings = serializers.BooleanField(required=False)


class UpdateMRProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "first_name",
            "last_name",
            "phone",
            "address",
            "profile_image_url",
            "is_active",
        ]


class SessionRegisterSerializer(serializers.Serializer):
    device_id = serializers.CharField()
    device_info = serializers.CharField(required=False, allow_blank=True)


class UserSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserSession
        fields = [
            "id",
            "device_id",
            "device_info",
            "login_time",
            "last_activity",
            "is_active",
        ]
