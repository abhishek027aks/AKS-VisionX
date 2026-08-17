from django.db import models


class Detection(models.Model):
    class ObjectType(models.TextChoices):
        PERSON = "PERSON", "Person"
        VEHICLE = "VEHICLE", "Vehicle"
        ANIMAL = "ANIMAL", "Animal"
        WEAPON = "WEAPON", "Weapon"
        OBJECT = "OBJECT", "Object"
        UNKNOWN = "UNKNOWN", "Unknown"

    class DetectionStatus(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        ENDED = "ENDED", "Ended"

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="detections",
    )

    camera = models.ForeignKey(
        "cameras.Camera",
        on_delete=models.CASCADE,
        related_name="detections",
    )

    event = models.ForeignKey(
        "events.Event",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="detections",
    )

    object_type = models.CharField(
        max_length=20,
        choices=ObjectType.choices,
    )

    label = models.CharField(
        max_length=100,
        blank=True,
    )

    confidence = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
    )

    tracking_id = models.CharField(
        max_length=100,
        blank=True,
        db_index=True,
    )

    status = models.CharField(
        max_length=20,
        choices=DetectionStatus.choices,
        default=DetectionStatus.ACTIVE,
    )

    first_seen_at = models.DateTimeField()
    last_seen_at = models.DateTimeField()

    # Bounding box coordinates.
    # Values are normalized between 0 and 1.
    bbox_x = models.DecimalField(
        max_digits=8,
        decimal_places=6,
        null=True,
        blank=True,
    )

    bbox_y = models.DecimalField(
        max_digits=8,
        decimal_places=6,
        null=True,
        blank=True,
    )

    bbox_width = models.DecimalField(
        max_digits=8,
        decimal_places=6,
        null=True,
        blank=True,
    )

    bbox_height = models.DecimalField(
        max_digits=8,
        decimal_places=6,
        null=True,
        blank=True,
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
                name="detect_org_time_idx",
            ),
            models.Index(
                fields=["camera", "-last_seen_at"],
                name="detect_camera_time_idx",
            ),
            models.Index(
                fields=["object_type", "-last_seen_at"],
                name="detect_type_time_idx",
            ),
            models.Index(
                fields=["tracking_id", "-last_seen_at"],
                name="detect_track_time_idx",
            ),
        ]

    def __str__(self):
        label = self.label or self.object_type
        return f"{label} - {self.camera.name}"
