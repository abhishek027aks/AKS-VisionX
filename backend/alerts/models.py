from django.db import models


class Alert(models.Model):
    class Severity(models.TextChoices):
        INFO = "INFO", "Info"
        LOW = "LOW", "Low"
        MEDIUM = "MEDIUM", "Medium"
        HIGH = "HIGH", "High"
        CRITICAL = "CRITICAL", "Critical"

    class Status(models.TextChoices):
        NEW = "NEW", "New"
        ACKNOWLEDGED = "ACKNOWLEDGED", "Acknowledged"
        RESOLVED = "RESOLVED", "Resolved"
        DISMISSED = "DISMISSED", "Dismissed"

    class Source(models.TextChoices):
        EVENT = "EVENT", "Event"
        SYSTEM = "SYSTEM", "System"
        STORAGE = "STORAGE", "Storage"
        CAMERA = "CAMERA", "Camera"

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="alerts",
    )

    camera = models.ForeignKey(
        "cameras.Camera",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="alerts",
    )

    event = models.ForeignKey(
        "events.Event",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="alerts",
    )

    source = models.CharField(
        max_length=20,
        choices=Source.choices,
        default=Source.EVENT,
    )

    severity = models.CharField(
        max_length=20,
        choices=Severity.choices,
        default=Severity.INFO,
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.NEW,
    )

    title = models.CharField(
        max_length=255,
    )

    message = models.TextField(
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    acknowledged_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    resolved_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["organization", "-created_at"],
                name="alert_org_time_idx",
            ),
            models.Index(
                fields=["severity", "-created_at"],
                name="alert_severity_time_idx",
            ),
            models.Index(
                fields=["status", "-created_at"],
                name="alert_status_time_idx",
            ),
        ]

    def __str__(self):
        return self.title
