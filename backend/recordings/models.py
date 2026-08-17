from django.db import models


class Recording(models.Model):
    class Status(models.TextChoices):
        RECORDING = "RECORDING", "Recording"
        COMPLETED = "COMPLETED", "Completed"
        FAILED = "FAILED", "Failed"
        DELETED = "DELETED", "Deleted"

    class Format(models.TextChoices):
        MP4 = "MP4", "MP4"
        MKV = "MKV", "MKV"
        TS = "TS", "MPEG-TS"
        OTHER = "OTHER", "Other"

    camera = models.ForeignKey(
        "cameras.Camera",
        on_delete=models.CASCADE,
        related_name="recordings",
    )

    stream = models.ForeignKey(
        "cameras.CameraStream",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="recordings",
    )

    storage_location = models.ForeignKey(
        "storage.StorageLocation",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="recordings",
    )

    file_path = models.TextField()

    file_name = models.CharField(
        max_length=255,
    )

    format = models.CharField(
        max_length=20,
        choices=Format.choices,
        default=Format.MP4,
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.RECORDING,
    )

    started_at = models.DateTimeField()

    ended_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    duration_seconds = models.PositiveIntegerField(
        null=True,
        blank=True,
    )

    file_size_bytes = models.BigIntegerField(
        default=0,
    )

    protected = models.BooleanField(
        default=False,
    )

    protection_reason = models.CharField(
        max_length=255,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["-started_at"]
        indexes = [
            models.Index(
                fields=["camera", "-started_at"],
                name="recording_camera_time_idx",
            ),
            models.Index(
                fields=["storage_location", "-started_at"],
                name="recording_storage_time_idx",
            ),
            models.Index(
                fields=["protected", "-started_at"],
                name="recording_protected_time_idx",
            ),
        ]

    def __str__(self):
        return self.file_name
