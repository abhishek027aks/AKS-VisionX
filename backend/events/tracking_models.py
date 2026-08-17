from django.db import models


class TrackingSession(models.Model):
    class ObjectType(models.TextChoices):
        PERSON = "PERSON", "Person"
        VEHICLE = "VEHICLE", "Vehicle"
        ANIMAL = "ANIMAL", "Animal"
        WEAPON = "WEAPON", "Weapon"
        OBJECT = "OBJECT", "Object"
        UNKNOWN = "UNKNOWN", "Unknown"

    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        ENDED = "ENDED", "Ended"

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="tracking_sessions",
    )

    camera = models.ForeignKey(
        "cameras.Camera",
        on_delete=models.CASCADE,
        related_name="tracking_sessions",
    )

    object_type = models.CharField(
        max_length=20,
        choices=ObjectType.choices,
    )

    tracking_id = models.CharField(
        max_length=100,
        db_index=True,
    )

    person_profile = models.ForeignKey(
        "events.PersonProfile",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tracking_sessions",
    )

    vehicle_profile = models.ForeignKey(
        "events.VehicleProfile",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tracking_sessions",
    )

    label = models.CharField(
        max_length=200,
        blank=True,
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
    )

    first_seen_at = models.DateTimeField()
    last_seen_at = models.DateTimeField()

    first_seen_x = models.DecimalField(
        max_digits=8,
        decimal_places=6,
        null=True,
        blank=True,
    )

    first_seen_y = models.DecimalField(
        max_digits=8,
        decimal_places=6,
        null=True,
        blank=True,
    )

    last_seen_x = models.DecimalField(
        max_digits=8,
        decimal_places=6,
        null=True,
        blank=True,
    )

    last_seen_y = models.DecimalField(
        max_digits=8,
        decimal_places=6,
        null=True,
        blank=True,
    )

    total_distance = models.DecimalField(
        max_digits=12,
        decimal_places=6,
        default=0,
    )

    camera_count = models.PositiveIntegerField(
        default=1,
    )

    zone_count = models.PositiveIntegerField(
        default=0,
    )

    total_detections = models.PositiveIntegerField(
        default=0,
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
        ordering = ["-last_seen_at"]
        indexes = [
            models.Index(
                fields=["organization", "-last_seen_at"],
                name="track_org_time_idx",
            ),
            models.Index(
                fields=["camera", "-last_seen_at"],
                name="track_camera_time_idx",
            ),
            models.Index(
                fields=["tracking_id", "-last_seen_at"],
                name="track_id_time_idx",
            ),
            models.Index(
                fields=["object_type", "-last_seen_at"],
                name="track_type_time_idx",
            ),
            models.Index(
                fields=["status", "-last_seen_at"],
                name="track_status_time_idx",
            ),
        ]
    @property
    def duration_seconds(self):
        if not self.first_seen_at or not self.last_seen_at:
            return 0

        duration = self.last_seen_at - self.first_seen_at

        return max(
            0,
            int(duration.total_seconds()),
        )

    def __str__(self):
        return f"{self.object_type}:{self.tracking_id} - {self.camera.name}"


