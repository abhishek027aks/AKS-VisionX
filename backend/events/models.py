from django.db import models


class Event(models.Model):
    class EventType(models.TextChoices):
        MOTION = "MOTION", "Motion"
        PERSON = "PERSON", "Person"
        VEHICLE = "VEHICLE", "Vehicle"
        ANPR = "ANPR", "ANPR / Number Plate"
        TRAFFIC = "TRAFFIC", "Traffic"
        INTRUSION = "INTRUSION", "Intrusion"
        LINE_CROSSING = "LINE_CROSSING", "Line Crossing"
        LOITERING = "LOITERING", "Loitering"
        OBJECT = "OBJECT", "Object"
        AUDIO = "AUDIO", "Audio"
        CAMERA_OFFLINE = "CAMERA_OFFLINE", "Camera Offline"
        SYSTEM = "SYSTEM", "System"
        OTHER = "OTHER", "Other"

    class Status(models.TextChoices):
        NEW = "NEW", "New"
        ACKNOWLEDGED = "ACKNOWLEDGED", "Acknowledged"
        RESOLVED = "RESOLVED", "Resolved"
        DISMISSED = "DISMISSED", "Dismissed"

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="events",
    )

    camera = models.ForeignKey(
        "cameras.Camera",
        on_delete=models.CASCADE,
        related_name="events",
    )

    recording = models.ForeignKey(
        "recordings.Recording",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="events",
    )

    event_type = models.CharField(
        max_length=30,
        choices=EventType.choices,
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.NEW,
    )

    title = models.CharField(
        max_length=255,
    )

    description = models.TextField(
        blank=True,
    )

    occurred_at = models.DateTimeField()

    confidence = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
    )

    snapshot_path = models.TextField(
        blank=True,
    )

    protected = models.BooleanField(
        default=True,
    )

    metadata = models.JSONField(
        default=dict,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["-occurred_at"]
        indexes = [
            models.Index(
                fields=["organization", "-occurred_at"],
                name="event_org_time_idx",
            ),
            models.Index(
                fields=["camera", "-occurred_at"],
                name="event_camera_time_idx",
            ),
            models.Index(
                fields=["event_type", "-occurred_at"],
                name="event_type_time_idx",
            ),
            models.Index(
                fields=["status", "-occurred_at"],
                name="event_status_time_idx",
            ),
        ]

    def __str__(self):
        return f"{self.title} - {self.occurred_at}"

from .detection_models import Detection

from .identity_models import PersonProfile, VehicleProfile

from .tracking_models import TrackingSession

from .tracking_point_models import TrackingPoint

from .tracking_location_models import TrackingLocation

from .tracking_camera_visit_models import TrackingCameraVisit

from .identity_match_models import IdentityMatch
