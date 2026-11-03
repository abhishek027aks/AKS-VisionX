from django.db import models


class TrackingCameraVisit(models.Model):
    tracking_session = models.ForeignKey(
        "events.TrackingSession",
        on_delete=models.CASCADE,
        related_name="camera_visits",
    )

    camera = models.ForeignKey(
        "cameras.Camera",
        on_delete=models.CASCADE,
        related_name="tracking_camera_visits",
    )

    entered_at = models.DateTimeField()

    exited_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    duration_seconds = models.PositiveIntegerField(
        default=0,
    )

    first_x = models.DecimalField(
        max_digits=8,
        decimal_places=6,
        null=True,
        blank=True,
    )

    first_y = models.DecimalField(
        max_digits=8,
        decimal_places=6,
        null=True,
        blank=True,
    )

    last_x = models.DecimalField(
        max_digits=8,
        decimal_places=6,
        null=True,
        blank=True,
    )

    last_y = models.DecimalField(
        max_digits=8,
        decimal_places=6,
        null=True,
        blank=True,
    )

    detection_count = models.PositiveIntegerField(
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
        ordering = ["entered_at"]
        indexes = [
            models.Index(
                fields=["tracking_session", "entered_at"],
                name="track_cam_visit_session_idx",
            ),
            models.Index(
                fields=["camera", "-entered_at"],
                name="track_cam_visit_camera_idx",
            ),
        ]

    def __str__(self):
        return f"{self.tracking_session.tracking_id} - {self.camera.name}"
