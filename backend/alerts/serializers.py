from django.utils import timezone
from rest_framework import serializers

from cameras.models import Camera
from events.models import Event

from .models import Alert


class AlertSerializer(serializers.ModelSerializer):
    organization = serializers.PrimaryKeyRelatedField(
        read_only=True,
    )

    class Meta:
        model = Alert
        fields = [
            "id",
            "organization",
            "camera",
            "event",
            "source",
            "severity",
            "status",
            "title",
            "message",
            "created_at",
            "acknowledged_at",
            "resolved_at",
        ]
        read_only_fields = [
            "id",
            "organization",
            "created_at",
            "acknowledged_at",
            "resolved_at",
        ]

    def validate_camera(self, camera):
        request = self.context.get("request")
        user = request.user if request else None

        if (
            user
            and user.is_authenticated
            and user.groups.filter(
                name="Super Admin"
            ).exists()
        ):
            return camera

        if not user or not user.organization_id:
            raise serializers.ValidationError(
                "User is not assigned to an organization."
            )

        if camera.organization_id != user.organization_id:
            raise serializers.ValidationError(
                "You cannot access a camera from another organization."
            )

        return camera

    def validate_event(self, event):
        if event is None:
            return event

        request = self.context.get("request")
        user = request.user if request else None

        if (
            user
            and user.is_authenticated
            and user.groups.filter(
                name="Super Admin"
            ).exists()
        ):
            return event

        if not user or not user.organization_id:
            raise serializers.ValidationError(
                "User is not assigned to an organization."
            )

        if event.organization_id != user.organization_id:
            raise serializers.ValidationError(
                "You cannot access an event from another organization."
            )

        return event

    def validate(self, attrs):
        request = self.context.get("request")
        user = request.user if request else None

        camera = attrs.get(
            "camera",
            getattr(self.instance, "camera", None),
        )

        event = attrs.get(
            "event",
            getattr(self.instance, "event", None),
        )

        status = attrs.get(
            "status",
            getattr(
                self.instance,
                "status",
                Alert.Status.NEW,
            ),
        )

        is_super_admin = (
            user
            and user.is_authenticated
            and user.groups.filter(
                name="Super Admin"
            ).exists()
        )

        if camera is not None and event is not None:
            if camera.organization_id != event.organization_id:
                raise serializers.ValidationError(
                    {
                        "event": (
                            "Event must belong to the same "
                            "organization as the camera."
                        )
                    }
                )

        if not is_super_admin:
            if not user or not user.organization_id:
                raise serializers.ValidationError(
                    {
                        "organization": (
                            "User is not assigned to an organization."
                        )
                    }
                )

        if self.instance is None:
            if status != Alert.Status.NEW:
                raise serializers.ValidationError(
                    {
                        "status": (
                            "A new alert must start with NEW status."
                        )
                    }
                )

        else:
            current_status = self.instance.status

            allowed_transitions = {
                Alert.Status.NEW: {
                    Alert.Status.ACKNOWLEDGED,
                    Alert.Status.DISMISSED,
                },
                Alert.Status.ACKNOWLEDGED: {
                    Alert.Status.RESOLVED,
                    Alert.Status.DISMISSED,
                },
                Alert.Status.RESOLVED: set(),
                Alert.Status.DISMISSED: set(),
            }

            if status != current_status:
                if status not in allowed_transitions.get(
                    current_status,
                    set(),
                ):
                    raise serializers.ValidationError(
                        {
                            "status": (
                                f"Invalid alert status transition "
                                f"from {current_status} to {status}."
                            )
                        }
                    )

        return attrs

    def update(self, instance, validated_data):
        old_status = instance.status
        new_status = validated_data.get(
            "status",
            old_status,
        )

        instance = super().update(
            instance,
            validated_data,
        )

        now = timezone.now()

        if (
            old_status != Alert.Status.ACKNOWLEDGED
            and new_status == Alert.Status.ACKNOWLEDGED
        ):
            instance.acknowledged_at = now

        elif (
            new_status == Alert.Status.ACKNOWLEDGED
            and instance.acknowledged_at is None
        ):
            instance.acknowledged_at = now

        if (
            old_status != Alert.Status.RESOLVED
            and new_status == Alert.Status.RESOLVED
        ):
            instance.resolved_at = now

            if instance.acknowledged_at is None:
                instance.acknowledged_at = now

        elif (
            new_status == Alert.Status.RESOLVED
            and instance.resolved_at is None
        ):
            instance.resolved_at = now

            if instance.acknowledged_at is None:
                instance.acknowledged_at = now

        instance.save(
            update_fields=[
                "acknowledged_at",
                "resolved_at",
            ]
        )

        return instance
