from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from urllib.parse import urlparse

from cameras.models import Camera, CameraStream
from events.models import (
    Detection,
    TrackingPoint,
    TrackingLocation,
    TrackingCameraVisit,
    Event,
    IdentityMatch,
    PersonProfile,
    VehicleProfile,
)

User = get_user_model()


class CurrentUserSerializer(serializers.ModelSerializer):
    roles = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "is_staff",
            "is_superuser",
            "is_active",
            "organization",
            "roles",
        ]
        read_only_fields = fields

    def get_roles(self, obj):
        return list(
            obj.groups.values_list("name", flat=True).order_by("name")
        )


class CameraStreamSerializer(serializers.ModelSerializer):
    camera = serializers.PrimaryKeyRelatedField(
        queryset=Camera.objects.all(),
    )

    class Meta:
        model = CameraStream
        fields = [
            "id",
            "camera",
            "name",
            "stream_type",
            "protocol",
            "url",
            "width",
            "height",
            "fps",
            "codec",
            "bitrate_kbps",
            "enabled",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
        ]

    def validate_camera(self, camera):
        request = self.context.get("request")
        user = request.user

        if user.groups.filter(name="Super Admin").exists():
            return camera

        if not user.organization_id:
            raise serializers.ValidationError(
                "User is not assigned to an organization."
            )

        if camera.organization_id != user.organization_id:
            raise serializers.ValidationError(
                "You cannot access a camera from another organization."
            )

        return camera


class CameraSerializer(serializers.ModelSerializer):
    streams = CameraStreamSerializer(many=True, read_only=True)
    main_stream_url = serializers.CharField(
        write_only=True,
        required=False,
        allow_blank=True,
    )
    main_stream = serializers.SerializerMethodField()

    credential_encrypted = serializers.CharField(
        write_only=True,
        required=False,
        allow_blank=True,
    )

    organization = serializers.PrimaryKeyRelatedField(
        read_only=True,
    )

    created_by = serializers.PrimaryKeyRelatedField(
        read_only=True,
    )

    class Meta:
        model = Camera
        fields = [
            "id",
            "organization",
            "created_by",
            "name",
            "manufacturer",
            "model",
            "serial_number",
            "description",
            "location",
            "connection_type",
            "host",
            "port",
            "username",
            "credential_encrypted",
            "main_stream_url",
            "main_stream",
            "onvif_supported",
            "rtsp_supported",
            "ptz_supported",
            "audio_supported",
            "ai_supported",
            "recording_enabled",
            "enabled",
            "status",
            "last_seen",
            "streams",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "organization",
            "created_by",
            "status",
            "last_seen",
            "streams",
            "main_stream",
            "created_at",
            "updated_at",
        ]

    def get_main_stream(self, obj):
        stream = (
            obj.streams
            .filter(
                stream_type=CameraStream.StreamType.MAIN,
                enabled=True,
            )
            .first()
        )

        if stream is None:
            return None

        return CameraStreamSerializer(stream).data

    def validate_main_stream_url(self, value):
        value = value.strip()

        if not value:
            return value

        parsed = urlparse(value)

        if parsed.scheme.lower() == "local":
            if parsed.netloc.isdigit() and parsed.path in ("", "/"):
                return value
            raise serializers.ValidationError(
                "Local camera source must use local://<device-index>."
            )

        if parsed.scheme.lower() not in ["rtsp", "http", "https"]:
            raise serializers.ValidationError(
                "Stream URL must start with rtsp://, http://, https://, or local://."
            )

        if not parsed.netloc:
            raise serializers.ValidationError(
                "Stream URL must include a host."
            )

        return value

    def validate(self, attrs):
        request = self.context.get("request")
        user = request.user if request else None
        connection_type = attrs.get(
            "connection_type",
            self.instance.connection_type if self.instance else None,
        )
        main_stream_url = attrs.get("main_stream_url")

        if (
            main_stream_url
            and urlparse(main_stream_url).scheme.lower() == "local"
            and connection_type != Camera.ConnectionType.LOCAL
        ):
            raise serializers.ValidationError(
                {
                    "connection_type": (
                        "Select Local for a local camera device source."
                    )
                }
            )

        if (
            connection_type == Camera.ConnectionType.LOCAL
            and main_stream_url
            and urlparse(main_stream_url).scheme.lower() != "local"
        ):
            raise serializers.ValidationError(
                {
                    "main_stream_url": (
                        "Local cameras must use local://<device-index>."
                    )
                }
            )

        if (
            self.instance is None
            and user
            and user.is_authenticated
            and not user.groups.filter(name="Super Admin").exists()
            and not user.organization_id
        ):
            raise serializers.ValidationError(
                {
                    "organization": (
                        "User is not assigned to an organization."
                    )
                }
            )

        return attrs

    def _sync_main_stream(self, camera, stream_url):
        if stream_url is None:
            return

        stream_url = stream_url.strip()

        stream = (
            camera.streams
            .filter(stream_type=CameraStream.StreamType.MAIN)
            .first()
        )

        if not stream_url:
            if stream is not None:
                stream.enabled = False
                stream.save(update_fields=["enabled", "updated_at"])
            return

        if stream_url.lower().startswith("rtsp://"):
            protocol = CameraStream.Protocol.RTSP
        elif stream_url.lower().startswith("local://"):
            protocol = CameraStream.Protocol.OTHER
        else:
            protocol = CameraStream.Protocol.HTTP

        if stream is None:
            CameraStream.objects.create(
                camera=camera,
                name="Main Stream",
                stream_type=CameraStream.StreamType.MAIN,
                protocol=protocol,
                url=stream_url,
                enabled=True,
            )
            return

        stream.url = stream_url
        stream.protocol = protocol
        stream.enabled = True
        stream.save(
            update_fields=[
                "url",
                "protocol",
                "enabled",
                "updated_at",
            ]
        )

    def create(self, validated_data):
        credential = validated_data.pop(
            "credential_encrypted",
            "",
        )
        main_stream_url = validated_data.pop(
            "main_stream_url",
            None,
        )

        request = self.context["request"]
        user = request.user

        camera = Camera(
            organization=user.organization,
            created_by=user,
            **validated_data,
        )

        if credential:
            camera.set_credential(credential)

        camera.save()
        self._sync_main_stream(camera, main_stream_url)

        return camera

    def update(self, instance, validated_data):
        credential = validated_data.pop(
            "credential_encrypted",
            None,
        )
        main_stream_url = validated_data.pop(
            "main_stream_url",
            None,
        )

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if credential:
            instance.set_credential(credential)

        instance.save()
        self._sync_main_stream(instance, main_stream_url)

        return instance


class PersonProfileSerializer(serializers.ModelSerializer):
    organization = serializers.PrimaryKeyRelatedField(
        read_only=True,
    )

    class Meta:
        model = PersonProfile
        fields = [
            "id",
            "organization",
            "name",
            "category",
            "is_known",
            "is_active",
            "notes",
            "recognition_metadata",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "organization",
            "created_at",
            "updated_at",
        ]


class VehicleProfileSerializer(serializers.ModelSerializer):
    organization = serializers.PrimaryKeyRelatedField(
        read_only=True,
    )

    class Meta:
        model = VehicleProfile
        fields = [
            "id",
            "organization",
            "name",
            "category",
            "vehicle_type",
            "registration_number",
            "is_known",
            "is_active",
            "notes",
            "recognition_metadata",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "organization",
            "created_at",
            "updated_at",
        ]


class IdentityMatchSerializer(serializers.ModelSerializer):
    person = serializers.SerializerMethodField()
    vehicle = serializers.SerializerMethodField()

    tracking_id = serializers.CharField(
        source="tracking_session.tracking_id",
        read_only=True,
    )

    matched_at = serializers.DateTimeField(
        required=False,
        default=serializers.CreateOnlyDefault(timezone.now),
    )

    class Meta:
        model = IdentityMatch
        fields = [
            "id",
            "organization",
            "tracking_session",
            "tracking_id",
            "person_profile",
            "person",
            "vehicle_profile",
            "vehicle",
            "identity_type",
            "match_method",
            "confidence",
            "matched_at",
            "is_confirmed",
            "metadata",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "organization",
            "tracking_id",
            "person",
            "vehicle",
            "created_at",
            "updated_at",
        ]

    def validate(self, attrs):
        request = self.context.get("request")
        user = request.user if request else None

        tracking_session = attrs.get(
            "tracking_session",
            getattr(self.instance, "tracking_session", None),
        )

        person_profile = attrs.get(
            "person_profile",
            getattr(self.instance, "person_profile", None),
        )

        vehicle_profile = attrs.get(
            "vehicle_profile",
            getattr(self.instance, "vehicle_profile", None),
        )

        if tracking_session is None:
            raise serializers.ValidationError(
                {
                    "tracking_session": (
                        "Tracking session is required."
                    )
                }
            )

        # Super Admin can work across organizations.
        is_super_admin = (
            user
            and user.is_authenticated
            and user.groups.filter(
                name="Super Admin"
            ).exists()
        )

        if not is_super_admin:
            organization_id = getattr(
                user,
                "organization_id",
                None,
            )

            if not organization_id:
                raise serializers.ValidationError(
                    {
                        "organization": (
                            "User is not assigned to an organization."
                        )
                    }
                )

            if tracking_session.organization_id != organization_id:
                raise serializers.ValidationError(
                    {
                        "tracking_session": (
                            "You cannot use a tracking session "
                            "from another organization."
                        )
                    }
                )

            if (
                person_profile is not None
                and person_profile.organization_id != organization_id
            ):
                raise serializers.ValidationError(
                    {
                        "person_profile": (
                            "You cannot use a person profile "
                            "from another organization."
                        )
                    }
                )

            if (
                vehicle_profile is not None
                and vehicle_profile.organization_id != organization_id
            ):
                raise serializers.ValidationError(
                    {
                        "vehicle_profile": (
                            "You cannot use a vehicle profile "
                            "from another organization."
                        )
                    }
                )

        # Linked profiles must belong to the same organization
        # as the tracking session.
        tracking_organization_id = (
            tracking_session.organization_id
        )

        if (
            person_profile is not None
            and person_profile.organization_id
            != tracking_organization_id
        ):
            raise serializers.ValidationError(
                {
                    "person_profile": (
                        "Person profile must belong to the "
                        "same organization as the tracking session."
                    )
                }
            )

        if (
            vehicle_profile is not None
            and vehicle_profile.organization_id
            != tracking_organization_id
        ):
            raise serializers.ValidationError(
                {
                    "vehicle_profile": (
                        "Vehicle profile must belong to the "
                        "same organization as the tracking session."
                    )
                }
            )

        # Identity type must match the linked profile.
        identity_type = attrs.get(
            "identity_type",
            getattr(self.instance, "identity_type", None),
        )

        if identity_type == IdentityMatch.IdentityType.PERSON:
            if person_profile is None:
                raise serializers.ValidationError(
                    {
                        "person_profile": (
                            "Person profile is required for "
                            "PERSON identity matches."
                        )
                    }
                )

            if vehicle_profile is not None:
                raise serializers.ValidationError(
                    {
                        "vehicle_profile": (
                            "Vehicle profile cannot be used for "
                            "PERSON identity matches."
                        )
                    }
                )

        elif identity_type == IdentityMatch.IdentityType.VEHICLE:
            if vehicle_profile is None:
                raise serializers.ValidationError(
                    {
                        "vehicle_profile": (
                            "Vehicle profile is required for "
                            "VEHICLE identity matches."
                        )
                    }
                )

            if person_profile is not None:
                raise serializers.ValidationError(
                    {
                        "person_profile": (
                            "Person profile cannot be used for "
                            "VEHICLE identity matches."
                        )
                    }
                )

        return attrs

    def get_person(self, obj):
        if not obj.person_profile_id:
            return None

        return {
            "id": obj.person_profile.id,
            "name": obj.person_profile.name,
            "category": obj.person_profile.category,
        }

    def get_vehicle(self, obj):
        if not obj.vehicle_profile_id:
            return None

        return {
            "id": obj.vehicle_profile.id,
            "name": obj.vehicle_profile.name,
            "category": obj.vehicle_profile.category,
            "vehicle_type": obj.vehicle_profile.vehicle_type,
            "registration_number": obj.vehicle_profile.registration_number,
        }


class EventSerializer(serializers.ModelSerializer):
    organization = serializers.PrimaryKeyRelatedField(
        read_only=True,
    )

    class Meta:
        model = Event
        fields = [
            "id",
            "organization",
            "camera",
            "recording",
            "event_type",
            "status",
            "title",
            "description",
            "occurred_at",
            "confidence",
            "snapshot_path",
            "protected",
            "metadata",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "organization",
            "created_at",
            "updated_at",
        ]

    def validate_camera(self, camera):
        request = self.context.get("request")
        user = request.user

        if user.groups.filter(
            name="Super Admin"
        ).exists():
            return camera

        if not user.organization_id:
            raise serializers.ValidationError(
                "User is not assigned to an organization."
            )

        if camera.organization_id != user.organization_id:
            raise serializers.ValidationError(
                "You cannot access a camera from another organization."
            )

        return camera

    def validate_recording(self, recording):
        if recording is None:
            return recording

        request = self.context.get("request")
        user = request.user

        if user.groups.filter(
            name="Super Admin"
        ).exists():
            return recording

        if not user.organization_id:
            raise serializers.ValidationError(
                "User is not assigned to an organization."
            )

        if recording.organization_id != user.organization_id:
            raise serializers.ValidationError(
                "You cannot access a recording from another organization."
            )

        return recording

    def validate_status(self, status):
        instance = self.instance

        # CREATE: Event ????? NEW ?? ???? ????.
        if instance is None:
            if status != Event.Status.NEW:
                raise serializers.ValidationError(
                    "A new event must start with NEW status."
                )

            return status

        current_status = instance.status

        allowed_transitions = {
            Event.Status.NEW: {
                Event.Status.ACKNOWLEDGED,
                Event.Status.DISMISSED,
            },
            Event.Status.ACKNOWLEDGED: {
                Event.Status.RESOLVED,
                Event.Status.DISMISSED,
            },
            Event.Status.RESOLVED: set(),
            Event.Status.DISMISSED: set(),
        }

        if status == current_status:
            return status

        if status not in allowed_transitions.get(
            current_status,
            set(),
        ):
            raise serializers.ValidationError(
                f"Invalid event status transition: "
                f"{current_status} -> {status}."
            )

        return status
class PasswordChangeSerializer(serializers.Serializer):
    old_password = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
    )
    new_password = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
    )
    new_password_confirm = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
    )

    def validate(self, attrs):
        user = self.context["request"].user

        if not user.check_password(attrs["old_password"]):
            raise serializers.ValidationError(
                {"old_password": "Current password is incorrect."}
            )

        if attrs["old_password"] == attrs["new_password"]:
            raise serializers.ValidationError(
                {"new_password": "New password must be different from the current password."}
            )

        if attrs["new_password"] != attrs["new_password_confirm"]:
            raise serializers.ValidationError(
                {"new_password_confirm": "New passwords do not match."}
            )

        try:
            validate_password(attrs["new_password"], user=user)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(
                {"new_password": list(exc.messages)}
            )

        return attrs


from rest_framework_simplejwt.serializers import TokenObtainPairSerializer


class LoginTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    JWT login serializer with successful and failed login audit logging.
    """

    def validate(self, attrs):
        from audit.models import AuditLog

        request = self.context.get("request")
        username = attrs.get("username", "")

        try:
            data = super().validate(attrs)
        except Exception as exc:
            AuditLog.objects.create(
                user=None,
                organization=None,
                action=AuditLog.Action.LOGIN,
                result=AuditLog.Result.FAILURE,
                description="Failed login attempt.",
                ip_address=request.META.get("REMOTE_ADDR") if request else None,
                user_agent=request.META.get("HTTP_USER_AGENT", "") if request else "",
                metadata={
                    "authentication": "jwt",
                    "username": username,
                    "reason": str(exc),
                },
            )
            raise

        user = self.user

        AuditLog.objects.create(
            organization=user.organization,
            user=user,
            action=AuditLog.Action.LOGIN,
            result=AuditLog.Result.SUCCESS,
            description="User logged in successfully.",
            ip_address=request.META.get("REMOTE_ADDR") if request else None,
            user_agent=request.META.get("HTTP_USER_AGENT", "") if request else "",
            metadata={
                "authentication": "jwt",
            },
        )

        return data


class DetectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Detection
        fields = [
            "id",
            "organization",
            "camera",
            "event",
            "object_type",
            "label",
            "confidence",
            "tracking_id",
            "status",
            "first_seen_at",
            "last_seen_at",
            "bbox_x",
            "bbox_y",
            "bbox_width",
            "bbox_height",
            "metadata",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class TrackingPointSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrackingPoint
        fields = [
            "id",
            "tracking_session",
            "camera",
            "occurred_at",
            "x",
            "y",
            "width",
            "height",
            "confidence",
            "zone",
            "metadata",
            "created_at",
        ]
        read_only_fields = fields


class TrackingLocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrackingLocation
        fields = [
            "id",
            "tracking_session",
            "camera",
            "zone",
            "entered_at",
            "exited_at",
            "duration_seconds",
            "first_x",
            "first_y",
            "last_x",
            "last_y",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class TrackingCameraVisitSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrackingCameraVisit
        fields = [
            "id",
            "tracking_session",
            "camera",
            "entered_at",
            "exited_at",
            "duration_seconds",
            "first_x",
            "first_y",
            "last_x",
            "last_y",
            "detection_count",
            "metadata",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


