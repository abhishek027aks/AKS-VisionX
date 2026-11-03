from django.db import models


class TrackingPoint(models.Model):
    tracking_session = models.ForeignKey(
        "events.TrackingSession",
        on_delete=models.CASCADE,
        related_name="points",
    )

    camera = models.ForeignKey(
        "cameras.Camera",
        on_delete=models.CASCADE,
        related_name="tracking_points",
    )

    occurred_at = models.DateTimeField()

    x = models.DecimalField(
        max_digits=8,
        decimal_places=6,
        null=True,
        blank=True,
    )

    y = models.DecimalField(
        max_digits=8,
        decimal_places=6,
        null=True,
        blank=True,
    )

    width = models.DecimalField(
        max_digits=8,
        decimal_places=6,
        null=True,
        blank=True,
    )

    height = models.DecimalField(
        max_digits=8,
        decimal_places=6,
        null=True,
        blank=True,
    )

    confidence = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
    )

    zone = models.CharField(
        max_length=200,
        blank=True,
    )

    metadata = models.JSONField(
        default=dict,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["occurred_at"]
        indexes = [
            models.Index(
                fields=["tracking_session", "occurred_at"],
                name="track_point_session_time_idx",
            ),
            models.Index(
                fields=["camera", "-occurred_at"],
                name="track_point_camera_time_idx",
            ),
        ]

    def __str__(self):
        return f"{self.tracking_session.tracking_id} @ {self.occurred_at}"
