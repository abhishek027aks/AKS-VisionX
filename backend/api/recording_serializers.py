from pathlib import Path

from rest_framework import serializers

from recordings.models import Recording
from storage.models import StorageLocation


class RecordingSerializer(serializers.ModelSerializer):
    camera_name = serializers.CharField(
        source="camera.name",
        read_only=True,
    )
    storage_name = serializers.CharField(
        source="storage_location.name",
        read_only=True,
    )
    organization = serializers.IntegerField(
        source="camera.organization_id",
        read_only=True,
    )
    file_exists = serializers.SerializerMethodField()

    class Meta:
        model = Recording
        fields = [
            "id",
            "organization",
            "camera",
            "camera_name",
            "stream",
            "storage_location",
            "storage_name",
            "file_name",
            "format",
            "status",
            "started_at",
            "ended_at",
            "duration_seconds",
            "file_size_bytes",
            "protected",
            "protection_reason",
            "file_exists",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "organization",
            "camera_name",
            "storage_name",
            "file_exists",
            "status",
            "started_at",
            "ended_at",
            "duration_seconds",
            "file_size_bytes",
            "created_at",
            "updated_at",
        ]

    def get_file_exists(self, obj):
        try:
            return Path(obj.file_path).is_file()
        except (OSError, TypeError):
            return False


class StorageLocationSerializer(serializers.ModelSerializer):
    usage_percent = serializers.SerializerMethodField()
    max_size_bytes = serializers.SerializerMethodField()

    class Meta:
        model = StorageLocation
        fields = [
            "id",
            "organization",
            "name",
            "path",
            "storage_type",
            "enabled",
            "rolling_enabled",
            "max_size_gb",
            "current_size_bytes",
            "max_size_bytes",
            "usage_percent",
            "delete_oldest_unprotected",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "organization",
            "current_size_bytes",
            "max_size_bytes",
            "usage_percent",
            "created_at",
            "updated_at",
        ]

    def validate_path(self, value):
        if not Path(value).expanduser().is_absolute():
            raise serializers.ValidationError(
                "Recording folder path must be absolute."
            )

        return value

    def validate_max_size_gb(self, value):
        if value <= 0:
            raise serializers.ValidationError(
                "Maximum storage size must be greater than 0 GB."
            )

        return value

    def get_max_size_bytes(self, obj):
        from storage.storage_service import max_size_bytes

        return max_size_bytes(obj)

    def get_usage_percent(self, obj):
        maximum = self.get_max_size_bytes(obj)

        if maximum <= 0:
            return 0

        return round(
            (
                obj.current_size_bytes
                / maximum
            )
            * 100,
            2,
        )
