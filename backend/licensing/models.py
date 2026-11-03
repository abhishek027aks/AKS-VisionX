from django.db import models


class License(models.Model):
    class Edition(models.TextChoices):
        FREE = "FREE", "Free"
        PRO = "PRO", "Pro"
        BUSINESS = "BUSINESS", "Business"
        ENTERPRISE = "ENTERPRISE", "Enterprise"

    class Status(models.TextChoices):
        CREATED = "CREATED", "Created"
        ACTIVE = "ACTIVE", "Active"
        EXPIRED = "EXPIRED", "Expired"
        SUSPENDED = "SUSPENDED", "Suspended"
        REVOKED = "REVOKED", "Revoked"

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="licenses",
    )

    license_key = models.CharField(
        max_length=255,
        unique=True,
    )

    edition = models.CharField(
        max_length=20,
        choices=Edition.choices,
        default=Edition.FREE,
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.CREATED,
    )

    max_cameras = models.PositiveIntegerField(
        default=1,
    )

    max_users = models.PositiveIntegerField(
        default=1,
    )

    expires_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    activated_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    revoked_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    installation_id = models.CharField(
        max_length=255,
        blank=True,
    )

    feature_flags = models.JSONField(
        default=dict,
        blank=True,
    )

    notes = models.TextField(
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["organization", "-created_at"],
                name="license_org_time_idx",
            ),
            models.Index(
                fields=["status", "-created_at"],
                name="license_status_time_idx",
            ),
            models.Index(
                fields=["edition", "-created_at"],
                name="license_edition_time_idx",
            ),
            models.Index(
                fields=["installation_id"],
                name="license_installation_idx",
            ),
        ]

    def __str__(self):
        return f"{self.edition} - {self.license_key}"
